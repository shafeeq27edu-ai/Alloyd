"""Report rule-based classifier accuracy on the labeled prompt set.

Run from the backend directory:

    .venv/Scripts/python.exe scripts/evaluate_classifier.py

The prompt set lives in tests/data/classifier_prompts.json. Labels are the
category a user would expect for that phrasing, not the classifier's output.
"""
import base64
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The classifier imports the router, which imports provider adapters and the
# settings object. Use harmless placeholders so the report runs without keys.
os.environ.setdefault("SECRET_KEY", "classifier-evaluation-placeholder-secret-key")
os.environ.setdefault("ENCRYPTION_KEY", base64.urlsafe_b64encode(b"0" * 32).decode())
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")

from app.core.classifier import TaskClassifier  # noqa: E402
from app.core.router import TaskCategory  # noqa: E402

DATA_PATH = ROOT / "tests" / "data" / "classifier_prompts.json"


def load_samples() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def main() -> int:
    samples = load_samples()
    per_category: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    confusion: Counter[tuple[str, str]] = Counter()
    misses: list[tuple[str, str, str]] = []

    for sample in samples:
        expected = sample["category"]
        actual = TaskClassifier.classify(sample["prompt"]).value
        per_category[expected][1] += 1
        if expected == actual:
            per_category[expected][0] += 1
        else:
            misses.append((expected, actual, sample["prompt"]))
        confusion[(expected, actual)] += 1

    total = len(samples)
    correct = total - len(misses)
    print(f"Classifier accuracy on {total} labeled prompts")
    print(f"Overall: {correct}/{total} ({correct / total:.1%})\n")

    print("By category:")
    for category in TaskCategory:
        hit, seen = per_category[category.value]
        rate = f"{hit / seen:.1%}" if seen else "n/a"
        print(f"  {category.value:<18} {hit}/{seen} ({rate})")

    print("\nConfusion (expected -> predicted, wrong pairs only):")
    for (expected, actual), count in sorted(confusion.items()):
        if expected != actual:
            print(f"  {expected:<18} -> {actual:<18} {count}")

    print("\nMisclassified prompts:")
    for expected, actual, prompt in misses:
        print(f"  expected {expected:<18} predicted {actual:<18} {prompt}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
