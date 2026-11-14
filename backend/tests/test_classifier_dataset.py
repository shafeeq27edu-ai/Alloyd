import json
from collections import Counter
from pathlib import Path

from app.core.classifier import TaskClassifier
from app.core.router import TaskCategory

DATA_PATH = Path(__file__).resolve().parent / "data" / "classifier_prompts.json"

# Floor from the Phase 7 measurement (41/62 = 66.1%). It guards against a silent
# regression; raise it when the classifier's rules improve.
ACCURACY_FLOOR = 0.60


def _load() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def test_prompt_set_is_representative_and_unique():
    samples = _load()
    assert 50 <= len(samples) <= 100
    prompts = [sample["prompt"] for sample in samples]
    assert len(prompts) == len(set(prompts))
    labels = Counter(sample["category"] for sample in samples)
    assert set(labels) == {category.value for category in TaskCategory}
    assert min(labels.values()) >= 10


def test_classifier_accuracy_is_above_the_recorded_floor():
    samples = _load()
    correct = sum(
        1
        for sample in samples
        if TaskClassifier.classify(sample["prompt"]).value == sample["category"]
    )
    assert correct / len(samples) >= ACCURACY_FLOOR
