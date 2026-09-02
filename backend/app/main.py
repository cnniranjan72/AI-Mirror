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
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from app.db.postgres import init_pool, close_pool, run_schema, health as db_health
from app.api import ingest, query, profile, explain, seed, rl, auth_api, guardian, character, insights, privacy, timeline, graph, diary, goals, admin, orgs, research, settings as settings_api
from app.api import mirror
from app.api import calibration
from app.api import collection

load_dotenv()

from app.core.logging import configure_logging, log_with_context
from app.core.error_tracking import record_error

# Structured JSON logging
configure_logging(os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

# Upgrade path to a real error-tracking service, when one is configured —
# not built out further since no SENTRY_DSN exists in this environment today.
if os.getenv("SENTRY_DSN"):
    try:
        import sentry_sdk
        sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=0.1)
    except ImportError:
        logger.warning("SENTRY_DSN set but sentry_sdk is not installed")


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

_cors_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    trace_id = request.headers.get("X-Trace-Id", str(uuid.uuid4()))
    request.state.trace_id = trace_id
    logger.info("Request started", extra={"trace_id": trace_id, "path": request.url.path, "method": request.method})
    try:
        response = await call_next(request)
    except Exception as exc:
        # A plain @app.exception_handler(Exception) is unreliable here:
        # BaseHTTPMiddleware (which this middleware itself is, via
        # @app.middleware("http")) is documented to not consistently
        # propagate exceptions from deeper in the stack to app-level
        # exception handlers. This is the outermost middleware on every
        # request regardless, so catching here is both correct and simpler
        # than fighting that interaction.
        await record_error(exc, trace_id=trace_id, path=request.url.path, method=request.method)
        response = JSONResponse(
            status_code=500,
            content={"error": "internal_error", "trace_id": trace_id},
        )
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
app.include_router(auth_api.router, tags=["Auth"])
app.include_router(guardian.router, tags=["Guardian"])
app.include_router(character.router, tags=["Character"])
app.include_router(insights.router, tags=["Insights"])
app.include_router(mirror.router)
app.include_router(calibration.router, tags=["Calibration"])
app.include_router(collection.router, tags=["Collection"])
app.include_router(privacy.router, tags=["Privacy"])
app.include_router(timeline.router, tags=["Timeline"])
app.include_router(graph.router, tags=["Graph"])
app.include_router(diary.router, tags=["Diary"])
app.include_router(goals.router, tags=["Goals"])
app.include_router(admin.router, tags=["Admin"])
app.include_router(orgs.router, tags=["Organizations"])
app.include_router(research.router, tags=["Research"])
app.include_router(settings_api.router, tags=["Settings"])


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
    # Reported alongside the database because it is the same class of fact: a
    # dependency that can be down while the service is otherwise fine. It does
    # NOT affect overall status — answers remain correct without it, they are
    # just phrased deterministically.
    try:
        # MUST be the `backend.` path — see the note in app/api/settings.py.
        # Both spellings import successfully but are distinct module objects
        # with distinct singletons, and the pipeline uses the `backend.` one.
        from backend.verbalizer.verbalizer import get_verbalizer
        llm = get_verbalizer().phrasing_status()
    except Exception as e:
        llm = {"llm_phrasing_available": False, "disabled_reason": f"status unavailable: {e}"}

    return {
        "status": db.get("status", "unknown"),
        "timestamp": datetime.utcnow().isoformat(),
        "database": db,
        "llm": llm,
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
