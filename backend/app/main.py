"""
AIMirror Backend — FastAPI Application
Complete behavioral intelligence pipeline
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.db.postgres import init_pool, close_pool, run_schema, health as db_health
from app.api import ingest, query, profile, explain, seed, rl

load_dotenv()

from app.core.logging import configure_logging, log_with_context

# Structured JSON logging
configure_logging(os.getenv("LOG_LEVEL", "INFO"))
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


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    logger.info("Request started", extra={"trace_id": trace_id, "path": request.url.path, "method": request.method})
    response = await call_next(request)
    response.headers["X-Trace-Id"] = trace_id
    logger.info("Request completed", extra={"trace_id": trace_id, "status": response.status_code})
    return response

# Routes
app.include_router(ingest.router, tags=["Ingest"])
app.include_router(query.router, tags=["Query"])
app.include_router(profile.router, tags=["Profile"])
app.include_router(explain.router, tags=["Explainability"])
app.include_router(seed.router, tags=["Seed"])
app.include_router(rl.router, tags=["RL"])


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
