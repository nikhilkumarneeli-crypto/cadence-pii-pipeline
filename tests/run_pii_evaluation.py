import json
import sys
from pathlib import Path

# Add the project root to Python's import path.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.detection.engine import PIIDetector
from src.evaluation.evaluate import evaluate_dataset, save_report


BASE_DIR = Path(__file__).resolve().parent
DATASET_PATH = BASE_DIR / "pii_evaluation_dataset.json"
REPORT_PATH = BASE_DIR / "pii_evaluation_report.json"


def main():
    # Load labelled test cases.
    with DATASET_PATH.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    detector = PIIDetector()

    # Replace manually entered predictions with actual detector output.
    for case_name, case_data in dataset.items():
        text = case_data.get("text")

        if not text:
            print(
                f"Skipping {case_name}: no 'text' field is defined. "
                "Add the original input text to the dataset."
            )
            continue

        findings = detector.detect(text)

        case_data["predicted"] = [
            [finding.entity_type, finding.text]
            for finding in findings
        ]

    # Evaluate only cases with actual detector predictions.
    evaluated_dataset = {
        name: data
        for name, data in dataset.items()
        if data.get("text")
    }

    if not evaluated_dataset:
        raise ValueError(
            "No cases contain input text. Add a 'text' field "
            "to each case in pii_evaluation_dataset.json."
        )

    report = evaluate_dataset(evaluated_dataset)
    save_report(report, REPORT_PATH)

    print(json.dumps(report, indent=4))
    print(f"\nReport saved to: {REPORT_PATH}")


if __name__ == "__main__":
    main()
