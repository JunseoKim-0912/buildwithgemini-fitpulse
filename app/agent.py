# ruff: noqa
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import os
import sys
from zoneinfo import ZoneInfo

# Ensure bundled app directory is in sys.path so 'a2ui' imports resolve seamlessly
_app_dir = os.path.dirname(os.path.abspath(__file__))
if _app_dir not in sys.path:
    sys.path.insert(0, _app_dir)

from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.genai import types


from google.cloud import firestore

MODEL = "gemini-3.6-flash"

# CRITICAL: Hardcode GCP project ID as a string for Firestore client
PROJECT_ID = "qwiklabs-gcp-03-a5fda0a88d46"
db = firestore.Client(project=PROJECT_ID)


async def generate_memories_callback(callback_context: CallbackContext):
    """WRITE: after each turn, send the session to Memory Bank for extraction."""
    await callback_context.add_session_to_memory()
    return None


def record_workout_log(
    exercise_name: str,
    sets: int,
    reps: int,
    weight_kg: float = 0.0,
    notes: str = "",
    user_id: str = "user_demo",
) -> str:
    """Record an exercise or workout session performed by the user into Firestore.

    Args:
        exercise_name: Name of the exercise performed (e.g., Push-ups, Squats).
        sets: Number of sets completed.
        reps: Number of reps completed per set.
        weight_kg: Weight used in kg (0.0 for bodyweight).
        notes: Any additional notes or feedback on performance.
        user_id: ID of the user logging the workout.

    Returns:
        Confirmation message with document ID.
    """
    doc_data = {
        "user_id": user_id,
        "exercise_name": exercise_name,
        "sets": sets,
        "reps": reps,
        "weight_kg": weight_kg,
        "notes": notes,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    _, doc_ref = db.collection("workout_logs").add(doc_data)
    return f"Successfully logged workout '{exercise_name}' ({sets} sets of {reps} reps) with ID: {doc_ref.id}"


def get_recent_workout_logs(user_id: str = "user_demo", limit: int = 5) -> str:
    """Retrieve recent workout logs for a user from Firestore.

    Args:
        user_id: ID of the user whose workout logs to fetch.
        limit: Maximum number of recent workout logs to retrieve.

    Returns:
        Formatted string summarizing recent workouts.
    """
    query = (
        db.collection("workout_logs")
        .where("user_id", "==", user_id)
        .limit(limit)
    )
    docs = query.stream()
    logs = []
    for doc in docs:
        d = doc.to_dict()
        logs.append(
            f"- {d.get('exercise_name')}: {d.get('sets')} sets x {d.get('reps')} reps @ {d.get('weight_kg', 0)}kg (Notes: {d.get('notes', 'None')})"
        )
    if not logs:
        return f"No recent workout logs found for user {user_id}."
    return "Recent Workouts:\n" + "\n".join(logs)


def record_meal_log(
    meal_type: str,
    food_items: str,
    calories: int,
    protein_g: int = 0,
    carbs_g: int = 0,
    fat_g: int = 0,
    user_id: str = "user_demo",
) -> str:
    """Record a meal eaten by the user into Firestore to track nutrition.

    Args:
        meal_type: Type of meal (e.g. Breakfast, Lunch, Dinner, Snack).
        food_items: Description of food items eaten.
        calories: Estimated total calories consumed.
        protein_g: Grams of protein.
        carbs_g: Grams of carbohydrates.
        fat_g: Grams of fat.
        user_id: ID of the user logging the meal.

    Returns:
        Confirmation message with document ID.
    """
    doc_data = {
        "user_id": user_id,
        "meal_type": meal_type,
        "food_items": food_items,
        "calories": calories,
        "protein_g": protein_g,
        "carbs_g": carbs_g,
        "fat_g": fat_g,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    _, doc_ref = db.collection("meal_logs").add(doc_data)
    return f"Successfully logged {meal_type} ({calories} kcal) with ID: {doc_ref.id}"


def get_recent_meal_logs(user_id: str = "user_demo", limit: int = 5) -> str:
    """Retrieve recent meal logs and nutritional intake for a user from Firestore.

    Args:
        user_id: ID of the user whose meal logs to fetch.
        limit: Maximum number of recent meal logs to retrieve.

    Returns:
        Formatted string summarizing recent meals and calorie/macro totals.
    """
    query = (
        db.collection("meal_logs")
        .where("user_id", "==", user_id)
        .limit(limit)
    )
    docs = query.stream()
    logs = []
    total_calories = 0
    for doc in docs:
        d = doc.to_dict()
        cals = d.get("calories", 0)
        total_calories += cals
        logs.append(
            f"- {d.get('meal_type')}: {d.get('food_items')} ({cals} kcal, P: {d.get('protein_g')}g, C: {d.get('carbs_g')}g, F: {d.get('fat_g')}g)"
        )
    if not logs:
        return f"No recent meal logs found for user {user_id}."
    return f"Recent Meals (Total Calories: {total_calories} kcal):\n" + "\n".join(logs)


CORPUS_NAME = "projects/810401478372/locations/us-central1/ragCorpora/3777227061689581568"


def consult_herbal_corpus(query: str) -> str:
    """Search Culpeper's Complete Herbal corpus for matched passages about medicinal plants, herbs, natural remedies, and health guidance.

    Args:
        query: Search query string (plant name, herb, ailment, symptom, or natural remedy).
    Returns:
        The matched passages from the herbal corpus, or a note if none was found.
    """
    from vertexai.preview import rag
    import vertexai
    try:
        vertexai.init(project="qwiklabs-gcp-03-a5fda0a88d46", location="us-central1")
        resp = rag.retrieval_query(
            text=query,
            rag_resources=[rag.RagResource(rag_corpus=CORPUS_NAME)],
            rag_retrieval_config=rag.RagRetrievalConfig(top_k=5),
        )
        contexts = getattr(resp.contexts, "contexts", [])
        passages = [c.text.strip() for c in contexts if getattr(c, "text", "").strip()]
        return "\n\n---\n\n".join(passages) or "No relevant passage found."
    except Exception as e:
        return f"Retrieval failed: {e}"


def calculate_fitness_metrics(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str = "male",
    activity_level: str = "moderate",
    goal: str = "maintain",
) -> dict:
    """Calculate Basal Metabolic Rate (BMR), Total Daily Energy Expenditure (TDEE),
    target daily calories, and macro breakdown for a user.

    Args:
        weight_kg: Weight in kilograms.
        height_cm: Height in centimeters.
        age: Age in years.
        gender: Gender ('male' or 'female').
        activity_level: Activity level ('sedentary', 'light', 'moderate', 'active', 'very_active').
        goal: Fitness goal ('lose_weight', 'maintain', 'gain_muscle').

    Returns:
        Dict containing BMR, TDEE, target calories, and macro targets (protein_g, carbs_g, fat_g).
    """
    if gender.lower() == "female":
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) - 161
    else:
        bmr = (10 * weight_kg) + (6.25 * height_cm) - (5 * age) + 5

    activity_multipliers = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }
    mult = activity_multipliers.get(activity_level.lower(), 1.55)
    tdee = round(bmr * mult)

    goal_adjustments = {
        "lose_weight": -500,
        "maintain": 0,
        "gain_muscle": 300,
    }
    target_calories = tdee + goal_adjustments.get(goal.lower(), 0)

    protein_g = round(weight_kg * 2.0)
    fat_g = round((target_calories * 0.25) / 9)
    carbs_g = round((target_calories - (protein_g * 4) - (fat_g * 9)) / 4)

    return {
        "bmr": round(bmr),
        "tdee": tdee,
        "target_calories": target_calories,
        "protein_g": protein_g,
        "carbs_g": max(carbs_g, 0),
        "fat_g": fat_g,
        "goal": goal,
    }


def get_weather(query: str) -> str:
    """Simulates a web search. Use it get information on weather.

    Args:
        query: A string containing the location to get weather information for.

    Returns:
        A string with the simulated weather information for the queried location.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        return "It's 60 degrees and foggy."
    return "It's 90 degrees and sunny."


def get_current_time(query: str) -> str:
    """Simulates getting the current time for a city.

    Args:
        city: The name of the city to get the current time for.

    Returns:
        A string with the current time information.
    """
    if "sf" in query.lower() or "san francisco" in query.lower():
        tz_identifier = "America/Los_Angeles"
    else:
        return f"Sorry, I don't have timezone information for query: {query}."

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    return f"The current time for query {query} is {now.strftime('%Y-%m-%d %H:%M:%S %Z%z')}"


from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from .a2ui_utils import a2ui_callback

schema_manager = A2uiSchemaManager(
    version="0.8",
    catalogs=[BasicCatalog.get_config("0.8")],
)

instruction = schema_manager.generate_system_prompt(
    role_description=(
        "You are FitPulse, a personal trainer and nutrition coach AI assistant. "
        "You actively remember all user allergies, food intolerances, dietary restrictions, "
        "health metrics (age, height, weight, activity level), fitness goals, and historical "
        "workout/meal logs from previous conversations. ALWAYS ensure meal plans and advice "
        "strictly adhere to all remembered allergies and restrictions. "
        "When asked about herbal remedies, medicinal plants, or natural health advice, consult "
        "your grounded RAG tool (consult_herbal_corpus). "
        "Use your calculation tool (calculate_fitness_metrics) to compute personalized caloric and "
        "macro targets, and your Firestore logging tools (record_workout_log, get_recent_workout_logs, "
        "record_meal_log, get_recent_meal_logs) to track user workouts and daily nutrition."
    ),
    workflow_description="Analyze the request and return structured UI when appropriate.",
    ui_description=(
        "Keep every surface tiny and flat: ONE Card > ONE Column > a few Text rows. "
        "Never nest a Card inside a Card. "
        "Use ONLY these components: Card, Column, Row, Text, and Image. Do not use "
        "Table or Heading (unsupported), or Buttons, actions, or forms (they do "
        "nothing in adk web). "
        "You may include one Image component, but only when you have a public https "
        "URL for the image (for example the URL an image tool returns after uploading "
        "to a public bucket). Set the Image url to that exact https link, for example "
        '{"Image": {"url": {"literalString": "https://..."}}}. Never point an '
        "Image at a bare filename, an artifact name, or a non-http(s) path. If you do "
        "not have a public URL, add a short Text line noting the image instead. "
        "No markdown in text; use the usageHint property (\'h1\', \'h2\', \'body\') for "
        "headings and emphasis. "
        "Output ONLY the raw A2UI JSON array — no prose, and never wrap it in "
        "<a2a_datapart_json> tags or \'kind\'/\'data\'/\'metadata\' objects."
    ),
    include_schema=True,
    include_examples=True,
)


root_agent = Agent(
    name="root_agent",
    model=Gemini(
        model=MODEL,
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[
        PreloadMemoryTool(),
        consult_herbal_corpus,
        calculate_fitness_metrics,
        record_workout_log,
        get_recent_workout_logs,
        record_meal_log,
        get_recent_meal_logs,
        get_weather,
        get_current_time,
    ],
    after_agent_callback=generate_memories_callback,
    after_model_callback=a2ui_callback,
)

app = App(
    root_agent=root_agent,
    name="app",
)




