"""Command Line Interface and Batch Runner for Member 3 PPTX Engine.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.
"""

from __future__ import annotations
import sys
import os
import csv
import json
import argparse
from pathlib import Path
from typing import List, Dict, Any

from .extractor import PPTXExtractor
from .structure_metric import StructureMetricEngine, EvaluationResult
from .schema import PPTXExtractionResult


def run_pipeline(
    pptx_dir: str | Path,
    output_dir: str | Path,
    target_percent: float = 80.0,
) -> List[EvaluationResult]:
    """Run full extraction and structure evaluation across all PPTX files in a directory."""
    pptx_path = Path(pptx_dir)
    out_path = Path(output_dir)

    json_dir = out_path / "extracted_json"
    metrics_dir = out_path / "structure_metrics"
    csv_dir = out_path / "csv"
    reports_dir = out_path / "reports"

    json_dir.mkdir(parents=True, exist_ok=True)
    metrics_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    extractor = PPTXExtractor()
    metric_engine = StructureMetricEngine(target_percent=target_percent)

    eval_results: List[EvaluationResult] = []
    csv_rows: List[Dict[str, Any]] = []

    files = sorted(list(pptx_path.glob("*.pptx")))
    if not files:
        print(f"No .pptx files found in {pptx_dir}")
        return []

    print(f"\n{'='*75}")
    print(f"CADENCE FINANCIAL GROUP - MEMBER 3 PPTX EXTRACTION & EVALUATION")
    print(f"Processing {len(files)} presentation decks. Target: >= {target_percent}%")
    print(f"{'='*75}\n")

    for file in files:
        print(f"--> Extracting: {file.name} ...")
        res = extractor.extract(file)

        # Save JSON output
        json_file = json_dir / f"{file.stem}.json"
        res.save_json(json_file)

        # Run structure retention evaluation
        eval_res = metric_engine.evaluate(file, res)
        eval_results.append(eval_res)

        # Save metric JSON
        metric_file = metrics_dir / f"{file.stem}.json"
        with open(metric_file, "w", encoding="utf-8") as f:
            json.dump(eval_res.to_dict(), f, indent=2)

        # Build CSV row matching section 18 exact columns
        c_scores = eval_res.component_scores
        csv_row = {
            "file_name": file.name,
            "slides_total": eval_res.total_slides,
            "slides_extracted": res.extracted_slides,
            "text_blocks_expected": c_scores.get("text_block_preservation").expected_count if "text_block_preservation" in c_scores else 0,
            "text_blocks_extracted": c_scores.get("text_block_preservation").extracted_count if "text_block_preservation" in c_scores else 0,
            "tables_expected": c_scores.get("table_preservation").expected_count if "table_preservation" in c_scores else 0,
            "tables_extracted": c_scores.get("table_preservation").extracted_count if "table_preservation" in c_scores else 0,
            "table_cells_expected": c_scores.get("table_cell_preservation").expected_count if "table_cell_preservation" in c_scores else 0,
            "table_cells_extracted": c_scores.get("table_cell_preservation").extracted_count if "table_cell_preservation" in c_scores else 0,
            "charts_detected": c_scores.get("chart_text_preservation").expected_count if "chart_text_preservation" in c_scores else 0,
            "chart_text_extracted": c_scores.get("chart_text_preservation").extracted_count if "chart_text_preservation" in c_scores else 0,
            "speaker_notes_expected": c_scores.get("speaker_notes_preservation").expected_count if "speaker_notes_preservation" in c_scores else 0,
            "speaker_notes_extracted": c_scores.get("speaker_notes_preservation").extracted_count if "speaker_notes_preservation" in c_scores else 0,
            "images_detected": c_scores.get("ocr_preservation").expected_count if "ocr_preservation" in c_scores else 0,
            "images_ocr_processed": c_scores.get("ocr_preservation").extracted_count if "ocr_preservation" in c_scores else 0,
            "structure_score_percent": eval_res.overall_score_percent,
            "target_percent": eval_res.target_percent,
            "status": eval_res.status,
        }
        csv_rows.append(csv_row)

        print(f"    Result: {eval_res.overall_score_percent:.1f}% | Target: {eval_res.target_percent:.1f}% | Status: {eval_res.status}")

    # Write CSV
    csv_file = csv_dir / "structure_results.csv"
    if csv_rows:
        fieldnames = list(csv_rows[0].keys())
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"\n[+] Saved CSV summary to: {csv_file}")

    # Print summary table
    print(f"\n{'='*85}")
    print(f"{'File Name':<45} | {'Score':<8} | {'Target':<7} | {'Status':<6}")
    print(f"{'-'*85}")
    for r in eval_results:
        print(f"{r.file_name:<45} | {r.overall_score_percent:>6.1f}% | {r.target_percent:>5.1f}% | {r.status:<6}")
    print(f"{'='*85}\n")

    return eval_results


def main():
    parser = argparse.ArgumentParser(description="Cadence Member 3 PPTX Extractor CLI")
    parser.add_argument("--input-dir", "-i", default="test_data/pptx", help="Path to input PPTX directory")
    parser.add_argument("--output-dir", "-o", default="outputs", help="Path to output directory")
    parser.add_argument("--target", "-t", type=float, default=80.0, help="Structure retention target percent")
    args = parser.parse_args()

    run_pipeline(args.input_dir, args.output_dir, args.target)


if __name__ == "__main__":
    main()
