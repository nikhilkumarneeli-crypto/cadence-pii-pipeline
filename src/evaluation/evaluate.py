
"""
PII Detection Evaluation Module

Calculates:
- True positives, false positives, false negatives
- Precision, recall, and F1 score
- Metrics per PII type
- Metrics per file
- Overall dataset metrics

Expected and predicted items can be:
- Tuples: ("EMAIL", "person@example.com")
- Dictionaries containing entity_type and text
- PIIFinding objects from src.common.schema
"""

import json
from collections import Counter
from pathlib import Path


def _normalize_item(item):
    """
    Convert a detection into a consistent (entity_type, text) tuple.
    Supports tuples, dictionaries, and PIIFinding objects.
    """
    if isinstance(item, dict):
        entity_type = item["entity_type"]
        text = item["text"]

    elif isinstance(item, (tuple, list)) and len(item) == 2:
        entity_type, text = item

    else:
        entity_type = item.entity_type
        text = item.text

    return (
        str(entity_type).strip().upper(),
        " ".join(str(text).split()).casefold(),
    )


def _normalize_items(items):
    """Normalize a collection of PII findings."""
    return [_normalize_item(item) for item in items]


def _calculate_from_counts(tp, fp, fn):
    """Calculate standard classification metrics from counts."""

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall)
        else 0.0
    )

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def calculate_metrics(expected, predicted):
    """
    Calculate overall metrics for one file or test case.

    expected: ground-truth PII findings
    predicted: findings produced by the detector

    A match requires the same entity type and normalized text.
    """
    expected_items = Counter(_normalize_items(expected))
    predicted_items = Counter(_normalize_items(predicted))

    true_positives = sum(
        (expected_items & predicted_items).values()
    )
    false_positives = sum(
        (predicted_items - expected_items).values()
    )
    false_negatives = sum(
        (expected_items - predicted_items).values()
    )

    return _calculate_from_counts(
        true_positives,
        false_positives,
        false_negatives,
    )


def calculate_metrics_by_type(expected, predicted):
    """Calculate precision, recall, and F1 separately for each PII type."""

    expected_items = Counter(_normalize_items(expected))
    predicted_items = Counter(_normalize_items(predicted))

    entity_types = sorted(
        {entity_type for entity_type, _ in expected_items}
        | {entity_type for entity_type, _ in predicted_items}
    )

    metrics = {}

    for entity_type in entity_types:
        expected_for_type = Counter({
            item: count
            for item, count in expected_items.items()
            if item[0] == entity_type
        })

        predicted_for_type = Counter({
            item: count
            for item, count in predicted_items.items()
            if item[0] == entity_type
        })

        tp = sum(
            (expected_for_type & predicted_for_type).values()
        )
        fp = sum(
            (predicted_for_type - expected_for_type).values()
        )
        fn = sum(
            (expected_for_type - predicted_for_type).values()
        )

        metrics[entity_type] = _calculate_from_counts(tp, fp, fn)

    return metrics


def evaluate_file(expected, predicted):
    """Evaluate one file and return overall and per-type metrics."""

    return {
        "overall": calculate_metrics(expected, predicted),
        "by_type": calculate_metrics_by_type(expected, predicted),
    }


def evaluate_dataset(dataset):
    """
    Evaluate multiple files and calculate dataset-wide metrics.

    Input format:
    {
        "file1.txt": {
            "expected": [...],
            "predicted": [...]
        },
        "file2.txt": {
            "expected": [...],
            "predicted": [...]
        }
    }
    """

    per_file = {}

    total_tp = 0
    total_fp = 0
    total_fn = 0

    all_expected = []
    all_predicted = []

    for filename, data in dataset.items():
        expected = data["expected"]
        predicted = data["predicted"]

        file_result = evaluate_file(expected, predicted)
        per_file[filename] = file_result

        overall = file_result["overall"]

        total_tp += overall["true_positives"]
        total_fp += overall["false_positives"]
        total_fn += overall["false_negatives"]

        all_expected.extend(expected)
        all_predicted.extend(predicted)

    return {
        "overall": _calculate_from_counts(
            total_tp,
            total_fp,
            total_fn,
        ),
        "by_type": calculate_metrics_by_type(
            all_expected,
            all_predicted,
        ),
        "per_file": per_file,
    }


def save_report(report, output_path="evaluation_report.json"):
    """Save evaluation results as a readable JSON report."""

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4, ensure_ascii=False)

    return str(output_path)


def load_annotations(input_path):
    """
    Load a JSON dataset containing expected and predicted findings.

    Each file entry must contain 'expected' and 'predicted' lists.
    """

    with Path(input_path).open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, dict):
        raise ValueError("Dataset must be a JSON object.")

    for filename, data in dataset.items():
        if not isinstance(data, dict):
            raise ValueError(f"Invalid entry for {filename}.")

        if "expected" not in data or "predicted" not in data:
            raise ValueError(
                f"{filename} must contain 'expected' and 'predicted'."
            )

    return dataset


def main():
    """Run evaluation using a prepared JSON dataset."""

    import argparse

    parser = argparse.ArgumentParser(
        description="Evaluate PII detection results."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to JSON annotations and predictions.",
    )
    parser.add_argument(
        "--output",
        default="evaluation_report.json",
        help="Path for the output JSON report.",
    )

    args = parser.parse_args()

    try:
        dataset = load_annotations(args.input)
        report = evaluate_dataset(dataset)
        saved_path = save_report(report, args.output)

        print(json.dumps(report, indent=4))
        print(f"\nEvaluation report saved to: {saved_path}")

    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
