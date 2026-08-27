#!/usr/bin/env python3
"""Create serverless Vertex AI RAG corpus for FitPulse."""

import time
import vertexai
from vertexai.preview import rag
from vertexai.preview.rag.utils import resources as rr

PROJECT_ID = "qwiklabs-gcp-03-a5fda0a88d46"
LOCATION = "us-central1"
GCS_PATH = "gs://fitpulse-assets-qwiklabs-gcp-03-a5fda0a88d46/rag/pg49513.txt"

PARSING_PROMPT = (
    "Extract the individual useful facts, herbs, remedies, and nutritional descriptions in this text. "
    "Ignore and omit all boilerplate, publisher metadata, and legal disclaimers. "
    "Output clean, self-contained prose."
)

print("Step 1: Init Vertex AI...")
vertexai.init(project=PROJECT_ID, location=LOCATION)

print("Step 2: Update RAG Engine Config to Serverless...")
cfg_name = f"projects/{PROJECT_ID}/locations/{LOCATION}/ragEngineConfig"
try:
    rag.update_rag_engine_config(
        rag_engine_config=rag.RagEngineConfig(
            name=cfg_name,
            rag_managed_db_config=rag.RagManagedDbConfig(mode=rr.Serverless()),
        )
    )
    print("Engine config updated.")
except Exception as e:
    print("Config note:", e)

print("Step 3: Create Corpus...")
corpus = rag.create_corpus(
    display_name="fitpulse-herbal-corpus",
    embedding_model_config=rag.EmbeddingModelConfig(
        publisher_model="publishers/google/models/text-embedding-005"
    ),
)
print("CORPUS CREATED:", corpus.name)

print("Step 4: Import file...")
resp = rag.import_files(
    corpus_name=corpus.name,
    paths=[GCS_PATH],
    transformation_config=rag.TransformationConfig(
        chunking_config=rag.ChunkingConfig(chunk_size=512, chunk_overlap=100)
    ),
    llm_parser=rag.LlmParserConfig(
        model_name="gemini-2.5-flash",
        custom_parsing_prompt=PARSING_PROMPT,
    ),
)
print("IMPORT RESPONSE:", resp)
