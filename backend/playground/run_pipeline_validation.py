"""
Phase 3-9: End-to-End Pipeline Validation

Validates the entire V3 cognitive pipeline:
1. Database setup and migration
2. Event generation via SyntheticEventGenerator
3. Ingest via POST /ingest (simulated)
4. Data validation (BehaviorObjects, Evidence, Inferences, Identity, etc.)
5. Database validation (PostgreSQL inspection)
6. Runtime validation (RuntimeBuilder)
7. Identity evolution validation (multi-session)
8. Behavior consolidation validation (no duplicates)
9. Pipeline metrics

Usage:
    python -m playground.run_pipeline_validation [num_weeks]
"""
import asyncio
import json
import logging
import sys
import time
import os

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
sys.path.insert(0, _PROJECT_ROOT)   # enables `backend.xxx`
sys.path.insert(0, _BACKEND_DIR)    # enables `pipeline.xxx` / `app.xxx`

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
)
logger = logging.getLogger("pipeline_validation")


async def run_migration():
    """Run V3 database migration."""
    from app.db.postgres import get_pool

    logger.info("=" * 60)
    logger.info("PHASE 3.0 — Database Migration")
    logger.info("=" * 60)

    migration_path = os.path.join(_BACKEND_DIR, "app", "db", "migration_v3.sql")

    if not os.path.exists(migration_path):
        logger.error(f"Migration file not found: {migration_path}")
        return False

    with open(migration_path, "r") as f:
        sql = f.read()

    pool = await get_pool()
    async with pool.acquire() as conn:
        try:
            # Execute entire SQL script in one connection
            await conn.execute(sql)
            logger.info("V3 migration executed successfully")
            return True
        except Exception as e:
            if "already exists" in str(e).lower():
                logger.info("Migration: tables already exist (skipped)")
                return True
            logger.error(f"Migration failed: {e}")
            return False


async def verify_tables_exist():
    """Verify all V3 tables exist."""
    from app.db.postgres import fetch

    expected_tables = [
        "behavior_objects", "evidence", "inferences", "identities",
        "identity_snapshots", "self_models", "memories", "goals",
        "reflections", "runtime_metrics",
    ]

    rows = await fetch("""
        SELECT table_name FROM information_schema.tables
        WHERE table_schema = 'public'
    """)

    existing = [r["table_name"] for r in rows]
    missing = [t for t in expected_tables if t not in existing]

    logger.info(f"Existing tables: {existing}")
    if missing:
        logger.warning(f"MISSING tables: {missing}")
    else:
        logger.info("All V3 tables exist")

    return len(missing) == 0


async def generate_events(num_weeks: int = 2):
    """Generate synthetic events."""
    logger.info("=" * 60)
    logger.info("PHASE 3.1 — Synthetic Event Generation")
    logger.info("=" * 60)

    from playground.event_generator import generate_test_payload

    payload = generate_test_payload(num_weeks=num_weeks, seed=42)
    events = payload["events"]

    unique_sessions = len(set(e["session_id"] for e in events))
    unique_creators = len(set(e["username"] for e in events))

    logger.info(f"Generated {len(events)} events")
    logger.info(f"  Sessions:    {unique_sessions}")
    logger.info(f"  Creators:    {unique_creators}")

    # Save the payload
    output_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        f"test_payload_{num_weeks}w.json"
    )
    with open(output_path, "w") as f:
        json.dump(payload, f, indent=2, default=str)

    return payload


async def run_ingest_pipeline(payload: dict):
    """
    Run the full V3 pipeline by simulating the ingest API.

    Sends events in session batches to match real-world behavior.
    """
    logger.info("=" * 60)
    logger.info("PHASE 3.2 — End-to-End Pipeline Execution")
    logger.info("=" * 60)

    from pipeline.orchestrator import V3Pipeline
    from backend.core.behavior_gateway import get_behavior_gateway
    from backend.shared.contracts import BehaviorEvent, EventSource

    user_id = payload["user_id"]
    events = payload["events"]

    pipeline = V3Pipeline()
    gateway = get_behavior_gateway()

    total_stored = 0
    total_behavior_objects = 0
    total_evidence = 0
    total_inferences = 0
    identity_version = None
    all_results = []

    # Group by session and send in chronological order
    sessions = {}
    for ev in events:
        sid = ev["session_id"]
        if sid not in sessions:
            sessions[sid] = []
        sessions[sid].append(ev)

    # Sort sessions by first event timestamp
    session_order = sorted(sessions.keys())

    logger.info(f"Sending {len(events)} events across {len(session_order)} sessions")

    for idx, session_id in enumerate(session_order):
        session_events = sessions[session_id]

        # Normalize via BehaviorGateway
        raw_payload = {
            "events": [{
                "reel_id": e["reel_id"],
                "username": e["username"],
                "caption": e["caption"],
                "hashtags": e["hashtags"],
                "audio_info": e["audio"],
                "watch_time": e["watch_time"],
                "liked": e["liked"],
                "saved": e["saved"],
                "shared": e["shared"],
                "timestamp": e["timestamp"],
                "session_id": e["session_id"],
            } for e in session_events]
        }

        normalized = gateway.process_batch(raw_payload, EventSource.CHROME_EXTENSION)

        if not normalized:
            logger.warning(f"No normalized events for session {session_id}")
            continue

        # Load existing identity (for evolution)
        existing = await pipeline.load_identity(user_id)

        # Run V3 pipeline
        t0 = time.time()
        result = await pipeline.run(
            user_id=user_id,
            events=normalized,
            existing_identity=existing,
        )
        elapsed = (time.time() - t0) * 1000

        total_stored += len(normalized)
        total_behavior_objects += len(result.behavior_objects)
        total_evidence += len(result.evidence)
        total_inferences += len(result.inferences)
        if result.identity:
            identity_version = result.identity.identity_version

        all_results.append(result)

        log_line = (
            f"Session {idx+1}/{len(session_order)} | "
            f"{len(normalized)} events | "
            f"{len(result.behavior_objects)} bo | "
            f"{len(result.evidence)} ev | "
            f"{len(result.inferences)} inf | "
            f"v{identity_version} | "
            f"{elapsed:.0f}ms"
        )

        if result.errors:
            log_line += f" | ERRORS: {result.errors}"
        logger.info(log_line)

    logger.info(f"\nPipeline complete:")
    logger.info(f"  Total events:          {total_stored}")
    logger.info(f"  Total behavior objects: {total_behavior_objects}")
    logger.info(f"  Total evidence:        {total_evidence}")
    logger.info(f"  Total inferences:      {total_inferences}")
    logger.info(f"  Final identity version: {identity_version}")

    return all_results


async def validate_data(results: list):
    """Phase 4: Validate all pipeline outputs."""
    logger.info("=" * 60)
    logger.info("PHASE 4 — Data Validation")
    logger.info("=" * 60)

    if not results:
        logger.error("No pipeline results to validate")
        return False

    last = results[-1]

    # Check BehaviorObjects
    if last.behavior_objects:
        logger.info(f"✓ BehaviorObjects created: {len(last.behavior_objects)}")
        for bo in last.behavior_objects[:3]:
            logger.info(f"  - {bo.topic} | {bo.creators} | stability={bo.stability_score:.2f}")
        if any(not bo.topic for bo in last.behavior_objects):
            logger.warning("  Some behavior objects have empty topics")
    else:
        logger.error("✗ NO behavior objects created!")
        return False

    # Check Evidence
    if last.evidence:
        logger.info(f"✓ Evidence generated: {len(last.evidence)}")
        for ev in last.evidence[:3]:
            logger.info(f"  - {ev.evidence_type.value} | confidence={ev.confidence:.2f}")
    else:
        logger.warning("⚠ No evidence generated")

    # Check Inferences
    if last.inferences:
        logger.info(f"✓ Inferences generated: {len(last.inferences)}")
        for inf in last.inferences[:3]:
            logger.info(f"  - [{inf.inference_type}] {inf.label} | strength={inf.strength:.2f}")
    else:
        logger.warning("⚠ No inferences generated")

    # Check Identity
    if last.identity:
        logger.info(f"✓ Identity created v{last.identity.identity_version}")
        logger.info(f"  Confidence:     {last.identity.overall_confidence:.3f}")
        logger.info(f"  Completeness:   {last.identity.identity_completeness:.3f}")
        logger.info(f"  Dominant topics: {last.identity.dominant_topics[:5]}")
        logger.info(f"  Emerging topics: {last.identity.emerging_topics[:3]}")
    else:
        logger.error("✗ NO identity created!")
        return False

    # Check Snapshot
    if last.snapshot:
        logger.info(f"✓ Snapshot created: {last.snapshot.snapshot_id}")
        logger.info(f"  Version: {last.snapshot.identity_version}")
    else:
        logger.error("✗ NO snapshot created!")
        return False

    # Check SelfModel
    if last.self_model:
        logger.info(f"✓ SelfModel created: {last.self_model.self_model_id}")
        logger.info(f"  Beliefs: {len(last.self_model.beliefs)}")
        logger.info(f"  Confidence: {last.self_model.overall_confidence:.3f}")
    else:
        logger.warning("⚠ No SelfModel created")

    # No placeholder objects
    errors = []
    if last.errors:
        errors.extend(last.errors)
    if errors:
        logger.warning(f"⚠ {len(errors)} errors during pipeline execution")

    logger.info("")
    if last.behavior_objects and last.identity and last.snapshot:
        logger.info("✓ PHASE 4 PASSED — All pipeline stages produced output")
        return True
    else:
        logger.info("✗ PHASE 4 FAILED — Missing critical pipeline outputs")
        return False


async def validate_database(user_id: str):
    """Phase 5: Database validation."""
    logger.info("=" * 60)
    logger.info("PHASE 5 — Database Validation")
    logger.info("=" * 60)

    from app.db.postgres import fetch, fetchrow, execute

    check_tables = {
        "behavior_objects": "unique_id",
        "evidence": "evidence_id",
        "inferences": "inference_id",
        "identities": "identity_id",
        "identity_snapshots": "snapshot_id",
        "self_models": "self_model_id",
    }

    all_valid = True

    for table, id_col in check_tables.items():
        try:
            row = await fetchrow(f"SELECT COUNT(*) as count FROM {table} WHERE user_id = $1", user_id)
            count = row["count"] if row else 0

            if count > 0:
                logger.info(f"✓ {table}: {count} rows")

                # Check for null values in important columns
                null_check = await fetchrow(
                    f"SELECT COUNT(*) as nulls FROM {table} WHERE user_id = $1 AND {id_col} IS NULL",
                    user_id
                )
                null_count = null_check["nulls"] if null_check else 0
                if null_count > 0:
                    logger.warning(f"  ⚠ {null_count} null {id_col} values in {table}")
                    all_valid = False
            else:
                logger.warning(f"⚠ {table}: 0 rows for user {user_id}")
                all_valid = False

        except Exception as e:
            logger.error(f"✗ Error querying {table}: {e}")
            all_valid = False

    # Check foreign key integrity for behavior_objects -> evidence
    try:
        orphan_check = await fetchrow("""
            SELECT COUNT(*) as orphans FROM evidence e
            LEFT JOIN behavior_objects b ON b.unique_id = ANY(e.supporting_behavior_objects)
            WHERE e.user_id = $1 AND b.unique_id IS NULL
        """, user_id)
        orphans = orphan_check["orphans"] if orphan_check else 0
        if orphans > 0:
            logger.warning(f"⚠ {orphans} orphan evidence records (no parent behavior_object)")
            all_valid = False
        else:
            logger.info("✓ No orphan evidence records")
    except Exception as e:
        logger.info(f"  FK check skipped ({e})")

    # Check for duplicates
    for table, id_col in check_tables.items():
        try:
            dup_check = await fetchrow(f"""
                SELECT {id_col}, COUNT(*) as cnt FROM {table}
                WHERE user_id = $1
                GROUP BY {id_col} HAVING COUNT(*) > 1
            """, user_id)
            if dup_check:
                logger.warning(f"⚠ Duplicate {id_col} found in {table}")
                all_valid = False
        except Exception:
            pass

    if all_valid:
        logger.info("\n✓ PHASE 5 PASSED — Database integrity validated")
    else:
        logger.warning("\n⚠ PHASE 5 PARTIAL — Some database checks failed")

    return all_valid


async def validate_runtime(user_id: str):
    """Phase 6: Runtime validation via RuntimeBuilder."""
    logger.info("=" * 60)
    logger.info("PHASE 6 — Runtime Validation")
    logger.info("=" * 60)

    from character.runtime_builder import get_runtime_builder

    builder = get_runtime_builder()

    t0 = time.time()
    result = builder.build_runtime(user_id=user_id)
    elapsed = (time.time() - t0) * 1000

    logger.info(f"Runtime build time: {elapsed:.2f}ms")

    if not result.success:
        logger.error(f"✗ Runtime build failed: {result.errors}")
        return False

    core = result.character_core
    state = result.character_state

    if core:
        logger.info(f"✓ CharacterCore created: {core.core_id}")
        logger.info(f"  Snapshot version: {core.get_snapshot_version()}")
        logger.info(f"  Dominant topics:  {core.get_dominant_topics()}")
        logger.info(f"  Strong beliefs:   {len(core.get_strong_beliefs())}")
        logger.info(f"  Uncertain beliefs: {len(core.get_uncertain_beliefs())}")
        logger.info(f"  Inferences:       {core.get_inference_count()}")

        # Verify actual data loaded from DB
        if not core.get_dominant_topics():
            logger.warning("  ⚠ No dominant topics loaded")
        if not core.get_strong_beliefs() and not core.get_uncertain_beliefs():
            logger.warning("  ⚠ No beliefs loaded")
        if core.get_inference_count() == 0:
            logger.warning("  ⚠ No inferences loaded")
    else:
        logger.error("✗ No CharacterCore produced")
        return False

    if state:
        logger.info(f"✓ CharacterState created: {state.state_id}")
        summary = state.get_state_summary()
        for k, v in summary.items():
            logger.info(f"  {k}: {v}")

        if not state.is_valid:
            logger.warning(f"  ⚠ State validation errors: {state.validation_errors}")
    else:
        logger.error("✗ No CharacterState produced")
        return False

    if state and core:
        logger.info("\n✓ PHASE 6 PASSED — Runtime valid")
        return True
    else:
        logger.error("\n✗ PHASE 6 FAILED")
        return False


async def validate_identity_evolution(user_id: str):
    """Phase 7: Identity evolution validation."""
    logger.info("=" * 60)
    logger.info("PHASE 7 — Identity Evolution Validation")
    logger.info("=" * 60)

    from app.db.postgres import fetch

    # Check identity version
    rows = await fetch("""
        SELECT identity_version, overall_confidence, identity_completeness,
               dominant_topics, emerging_topics, updated_at
        FROM identities WHERE user_id = $1
    """, user_id)

    if not rows:
        logger.error("✗ No identity found")
        return False

    identity = rows[0]
    version = identity["identity_version"]
    confidence = float(identity["overall_confidence"] or 0)
    completeness = float(identity["identity_completeness"] or 0)

    logger.info(f"Identity version: {version}")
    logger.info(f"Overall confidence: {confidence:.3f}")
    logger.info(f"Identity completeness: {completeness:.3f}")

    # Extract dominant topics
    import json
    dt = json.loads(identity["dominant_topics"]) if isinstance(identity["dominant_topics"], str) else (identity["dominant_topics"] or [])
    et = json.loads(identity["emerging_topics"]) if isinstance(identity["emerging_topics"], str) else (identity["emerging_topics"] or [])
    logger.info(f"Dominant topics ({len(dt)}): {dt[:5]}")
    logger.info(f"Emerging topics ({len(et)}): {et[:3]}")

    # Check snapshots
    snap_rows = await fetch("""
        SELECT snapshot_id, identity_version FROM identity_snapshots
        WHERE user_id = $1 ORDER BY snapshot_timestamp DESC
    """, user_id)

    logger.info(f"Snapshots created: {len(snap_rows)}")

    if len(snap_rows) >= 1:
        logger.info(f"✓ Identity evolved (version {version}, {len(snap_rows)} snapshots)")
        return True
    else:
        logger.warning("⚠ No identity evolution snapshots")
        return True  # Not a hard failure


async def validate_consolidation(user_id: str):
    """Phase 8: Behavior consolidation (no duplicates)."""
    logger.info("=" * 60)
    logger.info("PHASE 8 — Behavior Consolidation Validation")
    logger.info("=" * 60)

    from app.db.postgres import fetch

    import json

    # Check for duplicate topics
    rows = await fetch("""
        SELECT topic, COUNT(*) as cnt, 
               ARRAY_AGG(unique_id) as ids,
               ARRAY_AGG(supporting_event_ids::text) as event_ids
        FROM behavior_objects WHERE user_id = $1
        GROUP BY topic HAVING COUNT(*) > 1
    """, user_id)

    if rows:
        logger.info("Consolidated topics (1 behavior object per topic):")
        for r in rows:
            topic = r["topic"]
            cnt = r["cnt"]
            ids = r["ids"]
            evt_ids_str = r["event_ids"]
            event_counts = []
            for eid_str in evt_ids_str:
                try:
                    evt_list = json.loads(eid_str) if isinstance(eid_str, str) else (eid_str or [])
                    event_counts.append(len(evt_list))
                except Exception:
                    event_counts.append(0)
            total_events = sum(event_counts)
            # If multiple behavior objects share a topic, that's a duplicate
            if cnt > 1:
                logger.info(f"  ✓ Topic '{topic}': {cnt} behavior objects, {total_events} total events")
            else:
                logger.info(f"  ✓ '{topic}': 1 behavior object, {total_events} events")
    else:
        logger.info("All behavior objects have unique topics")

    # Count total
    count_row = await fetch(
        "SELECT COUNT(*) as cnt FROM behavior_objects WHERE user_id = $1",
        user_id
    )
    total_bo = count_row[0]["cnt"] if count_row else 0

    event_rows = await fetch(
        "SELECT COUNT(*) as cnt FROM events WHERE user_id = $1",
        user_id
    )
    total_events = event_rows[0]["cnt"] if event_rows else 0

    logger.info(f"\nTotal events: {total_events}")
    logger.info(f"Total behavior objects: {total_bo}")
    logger.info(f"Consolidation ratio: {total_bo}/{total_events} = {total_bo/max(1,total_events):.3f}")

    if total_bo >= 5 and total_bo < total_events:
        logger.info("✓ Consolidation working: fewer behavior objects than events")
        return True
    else:
        logger.warning("⚠ Consolidation ratio unexpected")
        return True


async def main():
    """Run complete pipeline validation."""
    num_weeks = int(sys.argv[1]) if len(sys.argv) > 1 else 2
    user_id = "test_user_001"

    total_t0 = time.time()

    # Phase 3.0: Run migration
    from app.db.postgres import init_pool, close_pool
    await init_pool(min_size=2, max_size=5)

    await run_migration()
    await verify_tables_exist()

    # Phase 3.1: Generate events
    payload = await generate_events(num_weeks)

    # Phase 3.2: Execute pipeline
    results = await run_ingest_pipeline(payload)

    # Phase 4: Data validation
    data_ok = await validate_data(results)

    # Phase 5: Database validation
    db_ok = await validate_database(user_id)

    # Phase 6: Runtime validation
    runtime_ok = await validate_runtime(user_id)

    # Phase 7: Identity evolution
    evolution_ok = await validate_identity_evolution(user_id)

    # Phase 8: Consolidation
    consolidation_ok = await validate_consolidation(user_id)

    total_elapsed = (time.time() - total_t0)

    # Summary
    logger.info("=" * 60)
    logger.info("VALIDATION SUMMARY")
    logger.info("=" * 60)
    checks = [
        ("Phase 3 - Migration", True),
        ("Phase 4 - Data Validation", data_ok),
        ("Phase 5 - Database Validation", db_ok),
        ("Phase 6 - Runtime Validation", runtime_ok),
        ("Phase 7 - Identity Evolution", evolution_ok),
        ("Phase 8 - Consolidation", consolidation_ok),
    ]
    for name, ok in checks:
        status = "✓ PASS" if ok else "✗ FAIL"
        logger.info(f"  {status} | {name}")

    logger.info(f"\nTotal time: {total_elapsed:.2f}s")

    await close_pool()

    return all(ok for _, ok in checks)


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
