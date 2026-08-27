"""FastAPI proxy and API backend for FitPulse Agent.

Features:
  - /chat: Forwards user prompt to deployed Reasoning Engine agent over A2A
  - /logs: Fetches workout and meal log history directly from Firestore for analytics & charts
"""

import os
import uuid

import google.auth
import google.auth.transport.requests
import httpx
from a2a.client import ClientConfig, ClientFactory
from a2a.types import (
    AgentCard,
    FilePart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TextPart,
    TransportProtocol,
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.cloud import firestore

RESOURCE = os.environ.get(
    "AGENT_ENGINE_RESOURCE_NAME",
    "projects/810401478372/locations/us-central1/reasoningEngines/1096562187834490880",
)
AGENT_DIRECTORY = os.environ.get("AGENT_DIRECTORY", "app")
LOCATION = RESOURCE.split("/locations/")[1].split("/")[0]

A2A_BASE = (
    f"https://{LOCATION}-aiplatform.googleapis.com/reasoningEngines/v1/"
    f"{RESOURCE}/api/a2a/{AGENT_DIRECTORY}"
)
A2A_CARD_URL = f"{A2A_BASE}/.well-known/agent-card.json"

_A2UI_MIME = "application/json+a2ui"

_creds, _ = google.auth.default(
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)


def _auth_headers() -> dict[str, str]:
    _creds.refresh(google.auth.transport.requests.Request())
    return {
        "Authorization": f"Bearer {_creds.token}",
        "Content-Type": "application/json",
    }


# Firestore client for log analytics
PROJECT_ID = "qwiklabs-gcp-03-a5fda0a88d46"
db = firestore.Client(project=PROJECT_ID)

app = FastAPI()


@app.exception_handler(Exception)
async def _json_errors(request: Request, exc: Exception):
    return JSONResponse(
        status_code=200,
        content={
            "parts": [{"kind": "text", "text": f"Error: {type(exc).__name__}: {exc}"}]
        },
    )


_contexts: dict[str, str] = {}
_card: AgentCard | None = None


async def _get_card(client: httpx.AsyncClient) -> AgentCard:
    global _card
    if _card is None:
        resp = await client.get(A2A_CARD_URL)
        resp.raise_for_status()
        card = AgentCard(**resp.json())
        card.url = A2A_BASE
        _card = card
    return _card


def _extract_parts(parts: list) -> list[dict]:
    out: list[dict] = []
    for p in parts:
        root = getattr(p, "root", p)
        if isinstance(root, TextPart) and getattr(root, "text", None):
            out.append({"kind": "text", "text": root.text})
        elif getattr(root, "data", None) is not None:
            d = root.data
            if isinstance(d, dict):
                meta = d.get("metadata") or getattr(root, "metadata", None) or {}
                mime = meta.get("mimeType") if isinstance(meta, dict) else None
                inner_data = d.get("data") if d.get("kind") == "data" and "data" in d else d
                if mime == _A2UI_MIME or (
                    isinstance(inner_data, dict)
                    and any(
                        k in inner_data
                        for k in (
                            "beginRendering",
                            "surfaceUpdate",
                            "dataModelUpdate",
                            "deleteSurface",
                        )
                    )
                ):
                    out.append({"kind": "a2ui", "data": inner_data})
                elif "text" in d and isinstance(d["text"], str):
                    out.append({"kind": "text", "text": d["text"]})
            elif isinstance(d, str):
                out.append({"kind": "text", "text": d})
        elif isinstance(root, FilePart):
            uri = getattr(getattr(root, "file", None), "uri", None)
            if uri:
                out.append({"kind": "text", "text": uri})
    return out


@app.post("/chat")
async def chat(req: Request):
    body = await req.json()
    message = body.get("message", "")
    user_id = body.get("user_id") or "web-user"
    parts: list[dict] = []

    async with httpx.AsyncClient(headers=_auth_headers(), timeout=120) as client:
        card = await _get_card(client)
        factory = ClientFactory(
            ClientConfig(
                supported_transports=[
                    TransportProtocol.jsonrpc,
                    TransportProtocol.http_json,
                ],
                httpx_client=client,
            )
        )
        a2a_client = factory.create(card)

        msg = Message(
            message_id=str(uuid.uuid4()),
            role=Role.user,
            parts=[Part(root=TextPart(text=message))],
            context_id=_contexts.get(user_id),
        )

        last_task = None
        got_artifact_update = False
        async for event in a2a_client.send_message(msg):
            if not isinstance(event, tuple):
                continue
            task, update = event
            if task is not None:
                last_task = task
                if getattr(task, "context_id", None):
                    _contexts[user_id] = task.context_id
            if isinstance(update, TaskArtifactUpdateEvent):
                got_artifact_update = True
                parts.extend(_extract_parts(update.artifact.parts))

        if not got_artifact_update and last_task is not None:
            for artifact in getattr(last_task, "artifacts", None) or []:
                parts.extend(_extract_parts(artifact.parts))

    if not parts:
        parts = [{"kind": "text", "text": "(The agent didn't return a reply.)"}]
    return JSONResponse({"parts": parts})


@app.get("/logs")
async def get_logs(user_id: str = "user_demo"):
    try:
        w_docs = db.collection("workout_logs").where("user_id", "==", user_id).limit(50).stream()
        workouts = []
        for doc in w_docs:
            d = doc.to_dict()
            d["id"] = doc.id
            workouts.append(d)

        m_docs = db.collection("meal_logs").where("user_id", "==", user_id).limit(50).stream()
        meals = []
        for doc in m_docs:
            d = doc.to_dict()
            d["id"] = doc.id
            meals.append(d)

        workouts.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)
        meals.sort(key=lambda x: str(x.get("timestamp", "")), reverse=True)

        return {"status": "success", "workouts": workouts, "meals": meals}
    except Exception as e:
        return {"status": "error", "message": str(e), "workouts": [], "meals": []}


app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
