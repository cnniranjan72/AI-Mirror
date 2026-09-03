import json
import pytest
import sys
import os
import uuid
from pathlib import Path
from datetime import datetime


class TestModuleImports:
    def test_pipeline_import(self):
        from cognitive_pipeline.pipeline import CognitivePipeline, PipelineTrace, CognitivePipelineResult
        assert CognitivePipeline is not None

    def test_explain_api_import(self):
        from app.api.explain import router
        assert router is not None

    def test_reflection_engine_import(self):
        from reasoning.reflection_engine import ReflectionEngine, Reflection
        assert ReflectionEngine is not None

    def test_evidence_engine_import(self):
        from reasoning.evidence_engine import EvidenceEngine, Evidence, EvidenceType
        assert EvidenceEngine is not None

    def test_identity_evolution_import(self):
        from identity.identity_evolution import IdentityEvolution
        assert IdentityEvolution is not None

    def test_llm_provider_import(self):
        from verbalizer.llm_provider import get_llm_call, openai_call, anthropic_call
        assert callable(get_llm_call)

    def test_cognitive_planning_import(self):
        from cognitive_planning.planner_orchestrator import PlannerOrchestrator
        from cognitive_planning.planner_models import IntentPlan, ReasoningPlan, ResponsePlan
        assert PlannerOrchestrator is not None

    def test_logging_module(self):
        from app.core.logging import configure_logging, stage_logger, log_with_context, StructuredFormatter
        assert configure_logging is not None

    def test_migration_v4_sql_exists(self):
        v4_path = Path(__file__).parent.parent / "app" / "db" / "migration_v4.sql"
        assert v4_path.exists()
        content = v4_path.read_text()
        assert "pipeline_traces" in content
        assert "cognitive_metrics" in content
        assert "ON DELETE CASCADE" in content

    def test_app_main_module_loads(self):
        import importlib
        import app.main
        assert hasattr(app.main, "app")
        routes = [r.path for r in app.main.app.routes]
        assert "/" in routes
        assert "/health" in routes


class TestPipelineTrace:
    def test_pipeline_trace_creation(self):
        from cognitive_pipeline.pipeline import PipelineTrace
        trace = PipelineTrace(user_id="test_user", query="test query")
        assert trace.user_id == "test_user"
        assert trace.query == "test query"
        assert trace.success is False
        assert trace.intent_type is None
        assert trace.errors == []

    def test_pipeline_trace_custom_values(self):
        from cognitive_pipeline.pipeline import PipelineTrace
        trace_id = str(uuid.uuid4())
        now = datetime.utcnow()
        trace = PipelineTrace(
            user_id="user2", query="hello",
            started_at=now, total_ms=150.5, success=True,
            intent_type="question", intent_confidence=0.95,
        )
        assert trace.user_id == "user2"
        assert trace.total_ms == 150.5
        assert trace.success is True
        assert trace.intent_confidence == 0.95

    def test_pipeline_result_defaults(self):
        from cognitive_pipeline.pipeline import CognitivePipelineResult
        result = CognitivePipelineResult(query="test query")
        assert result.query == "test query"
        assert result.total_time_ms == 0.0

    def test_identity_shift_method_exists(self):
        src_path = Path(__file__).parent.parent / "identity" / "identity_evolution.py"
        src = src_path.read_text()
        assert "_compute_identity_shift" in src


class TestEvidenceEngine:
    def test_evidence_type_enum_values(self):
        from reasoning.evidence_engine import EvidenceType
        expected_lower = {"behavioral", "temporal", "topical", "creator", "interaction"}
        actual = {t.value for t in EvidenceType}
        assert actual == expected_lower

    def test_evidence_has_required_fields(self):
        from reasoning.evidence_engine import Evidence
        fields = list(Evidence.model_fields.keys())
        for required in ("evidence_id", "evidence_type", "confidence", "weight"):
            assert required in fields, f"Missing field: {required}"

    def test_evidence_engine_created(self):
        from reasoning.evidence_engine import EvidenceEngine
        engine = EvidenceEngine()
        assert engine is not None


class TestReflectionEngine:
    def test_reflection_has_required_fields(self):
        from reasoning.reflection_engine import Reflection
        import inspect
        sig = inspect.signature(Reflection.__init__)
        params = list(sig.parameters.keys())
        for required in ("reflection_id", "user_id", "summary", "key_insights", "confidence"):
            assert required in params, f"Missing field: {required}"

    def test_reflection_engine_created(self):
        from reasoning.reflection_engine import ReflectionEngine
        engine = ReflectionEngine()
        assert engine is not None

    def test_reflection_engine_has_generate(self):
        from reasoning.reflection_engine import ReflectionEngine
        engine = ReflectionEngine()
        assert hasattr(engine, "generate_reflection")
        assert callable(engine.generate_reflection)


class TestStructuredLogging:
    def test_structured_formatter_output(self):
        from app.core.logging import StructuredFormatter
        import logging
        formatter = StructuredFormatter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname=__file__,
            lineno=1, msg="hello", args=(), exc_info=None
        )
        output = formatter.format(record)
        parsed = json.loads(output)
        assert parsed["message"] == "hello"
        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test"

    def test_logger_with_context(self):
        from app.core.logging import stage_logger
        logger = stage_logger("test", "test_stage")
        assert logger.logger.name == "test"

    def test_log_with_context_function(self):
        from app.core.logging import log_with_context
        import logging
        logger = logging.getLogger("test_logger")
        log_with_context(logger, "info", "test msg", trace_id="abc", user_id="user1")
        log_with_context(logger, "warning", "warn msg")


class TestExplainAPI:
    def test_explain_router_has_all_routes(self):
        from app.api.explain import router
        route_paths = sorted(route.path for route in router.routes)
        expected = sorted([
            "/identity/snapshot", "/identity/current", "/identity/self-model",
            "/identity/drift",
            "/identity/blind-spots",
            "/identity/restore-points",
            "/identity/restore",
            "/identity/space",
            "/identity/counterfactual",
            "/query/traces/{trace_id}/xray",
            "/reasoning/evidence", "/reasoning/inferences", "/reasoning/reflections",
            "/reasoning/contested",
            "/reasoning/lifecycle",
            "/reasoning/memories",
            "/reasoning/behavior-objects", "/query/traces", "/query/traces/{trace_id}",
            "/cognitive/metrics", "/cognitive/summary",
            "/explain/{trace_id}", "/explain/evidence/{evidence_id}", "/explain/identity/{identity_id}",
            "/search",
        ])
        assert route_paths == expected, f"Missing routes. Got: {route_paths}"

    def test_explain_endpoints_accept_user_id(self):
        from app.api.explain import router
        import inspect
        # These derive their scope from a path param (trace_id/evidence_id/
        # identity_id) or, for /search, aren't user-scoped at all — they
        # legitimately have no user_id parameter of their own.
        no_user_id_param = {
            "/query/traces/{trace_id}", "/explain/{trace_id}",
            "/explain/evidence/{evidence_id}", "/explain/identity/{identity_id}",
            "/search",
            # POST, so the user_id is a field of the request body rather than
            # a signature parameter. That shape has its own enforcement check
            # in test_auth_coverage.py (_body_identified_routes), which is
            # where this route is covered.
            "/identity/counterfactual",
            "/identity/restore",
        }
        for r in router.routes:
            sig = inspect.signature(r.endpoint)
            if r.path in no_user_id_param:
                continue
            assert "user_id" in sig.parameters, f"{r.path}: missing user_id param"


class TestMigrationSQL:
    def test_migration_v4_creates_tables(self):
        v4_path = Path(__file__).parent.parent / "app" / "db" / "migration_v4.sql"
        sql = v4_path.read_text()
        assert "CREATE TABLE IF NOT EXISTS pipeline_traces" in sql
        assert "CREATE TABLE IF NOT EXISTS cognitive_metrics" in sql

    def test_migration_v4_foreign_keys(self):
        v4_path = Path(__file__).parent.parent / "app" / "db" / "migration_v4.sql"
        sql = v4_path.read_text()
        assert "ON DELETE CASCADE" in sql
        assert "ON DELETE SET NULL" in sql

    def test_migration_v4_indexes(self):
        v4_path = Path(__file__).parent.parent / "app" / "db" / "migration_v4.sql"
        sql = v4_path.read_text()
        assert "idx_traces_user" in sql
        assert "idx_traces_created" in sql
        assert "idx_metrics_user" in sql
        assert "idx_evidence_user_type" in sql


class TestAppConfiguration:
    def test_app_has_expected_routes(self):
        import app.main as main_app
        routes = [r.path for r in main_app.app.routes]
        expected = ["/", "/health", "/ingest", "/query"]
        for ep in expected:
            assert ep in routes

    def test_cors_middleware_configured(self):
        import app.main as main_app
        from fastapi.middleware.cors import CORSMiddleware
        classes = [m.cls for m in main_app.app.user_middleware]
        assert CORSMiddleware in classes

    def test_ingest_module_no_import_errors(self):
        from app.api.ingest import router, IngestRequest, IngestResponse
        assert router is not None


class TestCognitivePlanning:
    def test_intent_plan_creation(self):
        from cognitive_planning.planner_models import IntentPlan, UserIntentType
        plan = IntentPlan(
            intent_type=UserIntentType.INFORMATION,
            intent_confidence=0.8,
        )
        assert plan.intent_type == UserIntentType.INFORMATION
        assert plan.intent_confidence == 0.8

    def test_reasoning_plan_has_mode(self):
        from cognitive_planning.planner_models import ReasoningPlan, ReasoningMode
        plan = ReasoningPlan(primary_mode=ReasoningMode.EVIDENCE_AGGREGATION)
        assert plan.primary_mode == ReasoningMode.EVIDENCE_AGGREGATION


class TestVerbalizer:
    def test_get_llm_call_default(self):
        from verbalizer.llm_provider import get_llm_call
        call_fn = get_llm_call()
        assert callable(call_fn)


class TestMainApp:
    def test_health_endpoint_exists(self):
        import app.main as main_app
        routes = [r.path for r in main_app.app.routes]
        assert "/health" in routes

    def test_root_endpoint_returns_info(self):
        import app.main as main_app
        routes = [r.path for r in main_app.app.routes]
        assert "/" in routes
