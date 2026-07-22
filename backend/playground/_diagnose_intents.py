"""Quick diagnostic to find classification errors."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.cognitive_planning.intent_planner import get_intent_planner
from backend.playground.intent_dataset import INTENT_DATASET

planner = get_intent_planner()
errors = []
for q, exp in INTENT_DATASET:
    plan = planner.classify(q)
    if plan.intent_type.value != exp:
        errors.append((q, exp, plan.intent_type.value, plan.intent_confidence))

print(f"Total errors: {len(errors)} out of {len(INTENT_DATASET)}")
print()
for q, exp, got, conf in errors:
    print(f"  FAIL: \"{q}\" -> got={got}(conf={conf:.3f}), expected={exp}")
