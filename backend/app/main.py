"""
AIMirror Backend — FastAPI Application
Complete behavioral intelligence pipeline
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.db.postgres import init_pool, close_pool, run_schema, health as db_health
from app.api import ingest, query, profile

load_dotenv()

# Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting AIMirror Backend...")
    print("[AIMirror] PostgreSQL Backend Running on :8000")
    await init_pool()
    await run_schema()
    logger.info("Database ready")
    yield
    # Shutdown
    await close_pool()
    logger.info("Shutdown complete")


app = FastAPI(
    title="AIMirror API",
    description="Behavioral intelligence pipeline: Extension → NLP → Embeddings → RAG → Persona → RL",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(ingest.router, tags=["Ingest"])
app.include_router(query.router, tags=["Query"])
app.include_router(profile.router, tags=["Profile"])


@app.get("/")
async def root():
    return {
        "name": "AIMirror API",
        "version": "2.0.0",
        "pipeline": "Extension → Enrich → Expand → Embed → RAG → Persona → RL",
    }


@app.get("/health")
async def health_check():
    db = await db_health()
    return {
        "status": db.get("status", "unknown"),
        "timestamp": datetime.utcnow().isoformat(),
        "database": db,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
