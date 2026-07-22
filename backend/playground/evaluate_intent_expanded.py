"""Evaluate intent classifier on 596-query expanded dataset."""
import sys, os, time, hashlib, json
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from backend.cognitive_planning.intent_planner import get_intent_planner
from backend.cognitive_planning.planner_models import UserIntentType
from playground.intent_dataset_expanded import EXPANDED_DATASET

planner = get_intent_planner()
all_intents = [e.value for e in UserIntentType]

tp = Counter()
fp = Counter()
fn = Counter()
confusion = {exp: {pred: 0 for pred in all_intents} for exp in all_intents}
confidence_by_class = defaultdict(list)

for query, expected_str in EXPANDED_DATASET:
    plan = planner.classify(query)
    predicted = plan.intent_type.value
    confusion[expected_str][predicted] += 1
    confidence_by_class[expected_str].append(plan.intent_confidence)
    if predicted == expected_str:
        tp[expected_str] += 1
    else:
        fp[predicted] += 1
        fn[expected_str] += 1

total = len(EXPANDED_DATASET)
correct = sum(tp.values())
accuracy = correct / total

per_class = {}
for intent in all_intents:
    tpc = tp.get(intent, 0)
    fpc = fp.get(intent, 0)
    fnc = fn.get(intent, 0)
    precision = tpc / (tpc + fpc) if (tpc + fpc) > 0 else 0.0
    recall = tpc / (tpc + fnc) if (tpc + fnc) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    confs = confidence_by_class.get(intent, [])
    per_class[intent] = {
        "total": tp[intent] + fn[intent],
        "correct": tpc,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "avg_confidence": round(sum(confs)/len(confs), 4) if confs else 0.0,
    }

macro_f1 = sum(pc["f1"] for pc in per_class.values()) / len(per_class)
micro_f1 = accuracy

# Errors
errors = []
for query, expected_str in EXPANDED_DATASET:
    plan = planner.classify(query)
    if plan.intent_type.value != expected_str:
        errors.append((query, expected_str, plan.intent_type.value, plan.intent_confidence))

print("=" * 78)
print("EXPANDED INTENT CLASSIFIER EVALUATION (596 queries)")
print("=" * 78)
print(f"\nTotal: {total}, Correct: {correct}, Accuracy: {accuracy:.4f}")
print(f"Macro F1: {macro_f1:.4f}, Micro F1: {micro_f1:.4f}")
print(f"Errors: {len(errors)}")

if errors:
    print(f"\nErrors (first 20):")
    for q, exp, got, conf in errors[:20]:
        print(f"  FAIL: \"{q}\" -> {got} (conf={conf:.3f}), expected={exp}")

print(f"\n{'Intent':<22} {'Total':>6} {'OK':>6} {'Prec':>8} {'Rec':>8} {'F1':>8} {'Conf':>8}")
print("-" * 78)
for intent in sorted(all_intents):
    m = per_class[intent]
    print(f"{intent:<22} {m['total']:>6} {m['correct']:>6} {m['precision']:>8.4f} {m['recall']:>8.4f} {m['f1']:>8.4f} {m['avg_confidence']:>8.4f}")

print(f"\nTotal errors: {len(errors)} out of {total}")
print("=" * 78)

# Output JSON for paper
result = {
    "total_queries": total,
    "correct": correct,
    "accuracy": round(accuracy, 4),
    "macro_f1": round(macro_f1, 4),
    "micro_f1": round(micro_f1, 4),
    "total_errors": len(errors),
    "per_class": per_class,
}
print(f"\nJSON: {json.dumps(result, indent=2)}")
