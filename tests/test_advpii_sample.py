from datasets import load_dataset
from src.detection.engine import PIIDetector

# 1. Load dataset & initialize detector
dataset = load_dataset("roei-ar/AdvPIIBench", split="train")
detector = PIIDetector()

# 2. Build reproducible evaluation sample
positive = [row for row in dataset if row["pii_spans"]][:10]
negative = [row for row in dataset if not row["pii_spans"]][:10]
sample = positive + negative

print(f"Total benchmark samples: {len(sample)} (Positive: {len(positive)}, Negative: {len(negative)})")
print("=" * 80)

# Metrics counters
stats = {
    "positive_samples": len(positive),
    "negative_samples": len(negative),
    "clean_negatives": 0,
    "false_positives": 0,
    "ip_address_notes": 0,
}

for i, row in enumerate(sample, start=1):
    text = row["llm_input"]
    expected = row["pii_spans"]
    findings = detector.detect(text)

    is_negative_sample = len(expected) == 0
    detected_items = [(f.entity_type, text[f.start:f.end], (f.start, f.end)) for f in findings]
    expected_items = [(p["type"], p["value"]) for p in expected]

    print(f"\nExample {i} | Total Length: {len(text)} chars | Expected Spans: {len(expected)}")
    
    # Safe preview: head and tail for readability
    if len(text) > 160:
        preview = f"{text[:80]!r} ... {text[-60:]!r}"
    else:
        preview = repr(text)
    print(f"Text Preview : {preview}")
    print(f"Expected     : {expected_items}")
    print(f"Detected     : {detected_items}")

    # Inspect context around each detection
    for f in findings:
        ctx_start = max(0, f.start - 30)
        ctx_end = min(len(text), f.end + 30)
        snippet = text[ctx_start:ctx_end].replace("\n", " ")
        print(f"   -> [{f.entity_type}] '{text[f.start:f.end]}' at ({f.start}:{f.end}) | Context: ...{snippet}...")

    # Benchmark-specific Negative Sample Diagnostics
    if is_negative_sample:
        if not findings:
            stats["clean_negatives"] += 1
        else:
            # Count detections separately for manual review because
            # benchmark labels may omit genuine PII.
            stats["false_positives"] += len(findings)

        has_ip = any(f.entity_type == "IP_ADDRESS" for f in findings)
        if has_ip:
            stats["ip_address_notes"] += 1
            print("   >>> NOTE: Negative label contains a detected IP address in input.")

print("\n" + "=" * 80)
print("EVALUATION SUMMARY")
print("=" * 80)
print(f"Clean Negative Examples (0 false alarms) : {stats['clean_negatives']}/{stats['negative_samples']}")
print(f"Total Spurious Detections on Negatives  : {stats['false_positives']}")
print(f"Negative Samples Triggering IP Notes    : {stats['ip_address_notes']}")
print("=" * 80)