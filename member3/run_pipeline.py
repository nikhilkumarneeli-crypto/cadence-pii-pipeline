"""Master End-to-End Pipeline Runner for Member 3.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.

Executes all pipeline phases in one click:
1. Synthetic Test Data & Ground Truth Generation
2. Automated Test Suite Execution (pytest)
3. PPTX Batch Extraction & 10-Component Structure Evaluation
4. CSV & Markdown/HTML Report Generation
5. Slide Deck Generation (member3_reliable_outcomes.pptx)
6. Evidence Rendering (01 to 11)
"""

import sys
import subprocess
from pathlib import Path


def main():
    root_dir = Path(__file__).resolve().parent

    print("\n" + "=" * 80)
    print("CADENCE FINANCIAL GROUP — CASE STUDY 2: TEXT ANALYSIS & PII DETECTION")
    print("MEMBER 3: POWERPOINT EXTRACTION & STRUCTURE RETENTION EVALUATION")
    print("=" * 80 + "\n")

    python_exe = sys.executable

    # Phase 1: Test Data Generation
    print("[1/6] Generating synthetic test datasets & ground truth...")
    res = subprocess.run(
        [python_exe, str(root_dir / "test_data" / "scripts" / "generate_synthetic_test_data.py")],
        cwd=root_dir,
    )
    if res.returncode != 0:
        print("[-] Error during test data generation.")
        sys.exit(res.returncode)

    # Phase 2: Automated Tests
    print("\n[2/6] Running automated test suite with pytest...")
    res = subprocess.run(
        [python_exe, "-m", "pytest", "-v"],
        cwd=root_dir,
    )
    if res.returncode != 0:
        print("[-] Some tests failed.")
    else:
        print("[+] All automated tests passed successfully!")

    # Phase 3: PPTX Extraction & Metric Evaluation
    print("\n[3/6] Running PPTX extraction & structure retention metric on all decks...")
    res = subprocess.run(
        [python_exe, "-m", "src.pptx_extractor.cli"],
        cwd=root_dir,
    )
    if res.returncode != 0:
        print("[-] Error during PPTX extraction pipeline.")
        sys.exit(res.returncode)

    # Phase 4: Reports Compilation
    print("\n[4/6] Compiling Markdown and interactive HTML reports...")
    res = subprocess.run(
        [python_exe, str(root_dir / "scripts" / "generate_reports.py")],
        cwd=root_dir,
    )
    if res.returncode != 0:
        print("[-] Error compiling reports.")
        sys.exit(res.returncode)

    # Phase 5: Presentation Slide Generation
    print("\n[5/6] Building Member 3 presentation slide deck (member3_reliable_outcomes.pptx)...")
    res = subprocess.run(
        [python_exe, str(root_dir / "scripts" / "generate_slide_deck.py")],
        cwd=root_dir,
    )
    if res.returncode != 0:
        print("[-] Error generating slide deck.")
        sys.exit(res.returncode)

    # Phase 6: Visual Evidence Rendering
    print("\n[6/6] Generating visual execution evidence (evidence/01 to 11)...")
    res = subprocess.run(
        [python_exe, str(root_dir / "scripts" / "generate_evidence_images.py")],
        cwd=root_dir,
    )
    if res.returncode != 0:
        print("[-] Error generating evidence images.")
        sys.exit(res.returncode)

    print("\n" + "=" * 80)
    print("COMPLETE PIPELINE FINISHED SUCCESSFULLY!")
    print("=" * 80)
    print("Deliverables Summary:")
    print(f"  • Extracted JSONs:    outputs/extracted_json/")
    print(f"  • Structure Metrics:  outputs/structure_metrics/")
    print(f"  • Results CSV:        outputs/csv/structure_results.csv")
    print(f"  • Technical Reports:  outputs/reports/member3_report.html & .md")
    print(f"  • Slide Deck:         deck/member3_reliable_outcomes.pptx")
    print(f"  • Speaking Notes:     deck/member3_speaking_notes.md")
    print(f"  • Evidence Files:     evidence/01_project_structure.png to 11_final_test_results.png")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
