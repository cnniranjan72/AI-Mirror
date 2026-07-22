"""
Intent Classifier Evaluation Framework

Computes accuracy, precision, recall, F1, macro F1, micro F1,
confusion matrix, per-class metrics, and confidence calibration.
"""
import sys
import os
import time
import logging
import math
from collections import Counter, defaultdict
from typing import List, Tuple, Dict, Any

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.dirname(_SCRIPT_DIR)
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
sys.path.insert(0, _PROJECT_ROOT)
sys.path.insert(0, _BACKEND_DIR)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("evaluate_intent")

from backend.cognitive_planning.intent_planner import get_intent_planner
from backend.cognitive_planning.planner_models import UserIntentType
from playground.intent_dataset import INTENT_DATASET


def evaluate() -> Dict[str, Any]:
    planner = get_intent_planner()

    # Intent label list
    all_intents = list(UserIntentType)
    intent_labels = [e.value for e in all_intents]

    # Confusion matrix: rows=expected, cols=predicted
    confusion: Dict[str, Dict[str, int]] = {
        exp: {pred: 0 for pred in intent_labels}
        for exp in intent_labels
    }

    # Per-class counters
    tp: Dict[str, int] = Counter()
    fp: Dict[str, int] = Counter()
    fn: Dict[str, int] = Counter()

    # Confidence tracking
    confidence_by_class: Dict[str, List[float]] = defaultdict(list)
    correct_confidences: List[float] = []
    incorrect_confidences: List[float] = []

    # Timing
    timings: List[float] = []

    for query, expected_str in INTENT_DATASET:
        t0 = time.perf_counter_ns()
        plan = planner.classify(query)
        elapsed_ns = time.perf_counter_ns() - t0
        timings.append(elapsed_ns / 1_000_000)  # ms

        predicted = plan.intent_type.value
        expected = expected_str

        confusion[expected][predicted] += 1
        confidence_by_class[expected].append(plan.intent_confidence)

        if predicted == expected:
            tp[expected] += 1
            correct_confidences.append(plan.intent_confidence)
        else:
            fp[predicted] += 1
            fn[expected] += 1
            incorrect_confidences.append(plan.intent_confidence)

    total = len(INTENT_DATASET)
    correct = sum(tp.values())
    accuracy = correct / total if total > 0 else 0.0

    # Per-class metrics
    per_class: Dict[str, Dict[str, float]] = {}
    for intent in intent_labels:
        tpc = tp.get(intent, 0)
        fpc = fp.get(intent, 0)
        fnc = fn.get(intent, 0)
        precision = tpc / (tpc + fpc) if (tpc + fpc) > 0 else 0.0
        recall = tpc / (tpc + fnc) if (tpc + fnc) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        confs = confidence_by_class.get(intent, [])
        avg_conf = sum(confs) / len(confs) if confs else 0.0
        per_class[intent] = {
            "total": tp[intent] + fn[intent],
            "correct": tpc,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "avg_confidence": round(avg_conf, 4),
        }

    # Macro F1
    macro_f1 = sum(pc["f1"] for pc in per_class.values()) / len(per_class)

    # Micro F1 = accuracy (since micro averaging = accuracy for multi-class)
    micro_f1 = accuracy

    # Timing stats
    timings.sort()
    avg_ms = sum(timings) / len(timings)
    median_ms = timings[len(timings) // 2]
    p95_ms = timings[int(len(timings) * 0.95)]

    # Confidence calibration
    avg_correct_conf = sum(correct_confidences) / len(correct_confidences) if correct_confidences else 0.0
    avg_incorrect_conf = sum(incorrect_confidences) / len(incorrect_confidences) if incorrect_confidences else 0.0

    # Confusion matrix display rows
    confusion_rows: List[str] = []
    confusion_rows.append(f"{'':>22} " + " ".join(f"{l[:6]:>6}" for l in intent_labels))
    for exp_label in intent_labels:
        row = f"{exp_label:>22} "
        for pred_label in intent_labels:
            val = confusion[exp_label][pred_label]
            row += f"{val:>6}"
        confusion_rows.append(row)

    return {
        "total_queries": total,
        "correct": correct,
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "micro_f1": round(micro_f1, 4),
        "per_class": per_class,
        "confusion_matrix": confusion_rows,
        "timing_ms": {
            "avg": round(avg_ms, 4),
            "median": round(median_ms, 4),
            "p95": round(p95_ms, 4),
            "min": round(min(timings), 4),
            "max": round(max(timings), 4),
        },
        "confidence_calibration": {
            "avg_correct_confidence": round(avg_correct_conf, 4),
            "avg_incorrect_confidence": round(avg_incorrect_conf, 4),
        },
    }


def print_report(results: Dict[str, Any]) -> None:
    sep = "=" * 78
    print(sep)
    print("INTENT CLASSIFIER EVALUATION REPORT")
    print(sep)

    print(f"\nTotal queries:  {results['total_queries']}")
    print(f"Correct:        {results['correct']}")
    print(f"Accuracy:       {results['accuracy']:.2%}")
    print(f"Macro F1:       {results['macro_f1']:.4f}")
    print(f"Micro F1:       {results['micro_f1']:.4f}")

    print(f"\n{'-' * 78}")
    print("PER-CLASS METRICS")
    print(f"{'-' * 78}")
    print(f"{'Intent':<22} {'Total':>6} {'OK':>6} {'Prec':>8} {'Rec':>8} {'F1':>8} {'Conf':>8}")
    print(f"{'-' * 78}")
    for intent, metrics in results["per_class"].items():
        print(
            f"{intent:<22} {metrics['total']:>6} {metrics['correct']:>6} "
            f"{metrics['precision']:>8.4f} {metrics['recall']:>8.4f} "
            f"{metrics['f1']:>8.4f} {metrics['avg_confidence']:>8.4f}"
        )

    print(f"\n{'-' * 78}")
    print("CONFUSION MATRIX")
    print(f"{'-' * 78}")
    for row in results["confusion_matrix"]:
        print(row)

    print(f"\n{'─' * 78}")
    print("TIMING")
    print(f"{'─' * 78}")
    print(f"  Average:    {results['timing_ms']['avg']:.4f} ms")
    print(f"  Median:     {results['timing_ms']['median']:.4f} ms")
    print(f"  95th pct:   {results['timing_ms']['p95']:.4f} ms")
    print(f"  Min:        {results['timing_ms']['min']:.4f} ms")
    print(f"  Max:        {results['timing_ms']['max']:.4f} ms")

    print(f"\n{'-' * 78}")
    print("CONFIDENCE CALIBRATION")
    print(f"{'-' * 78}")
    cal = results["confidence_calibration"]
    print(f"  Avg confidence (correct):   {cal['avg_correct_confidence']:.4f}")
    print(f"  Avg confidence (incorrect): {cal['avg_incorrect_confidence']:.4f}")

    print(f"\n{sep}")
    passed = results["accuracy"] >= 0.95
    print(f"OVERALL: {'PASS' if passed else 'FAIL'} "
          f"(accuracy={results['accuracy']:.2%}, threshold=95%)")
    print(sep)


if __name__ == "__main__":
    results = evaluate()
    print_report(results)
    passed = results["accuracy"] >= 0.95
    sys.exit(0 if passed else 1)
