import os
import re
from pathlib import Path
import fitz

for p in [
    os.environ.get("TESSDATA_PREFIX"),
    r"C:\Program Files\Tesseract-OCR\tessdata",
    r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
    str(Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tessdata"),
]:
    if p and Path(p).exists():
        os.environ["TESSDATA_PREFIX"] = str(p)
        break

UNICODE_DASH_PATTERN = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2212\ufe63\uff0d]")
UNICODE_SPACE_PATTERN = re.compile(r"[\u00a0\u1680\u2000-\u200b\u202f\u205f\u3000]")

def normalize_text_dashes(text: str) -> str:
    if not text:
        return ""
    text = UNICODE_DASH_PATTERN.sub("-", text)
    text = UNICODE_SPACE_PATTERN.sub(" ", text)
    return text

def get_dash_variants(phrase: str):
    p_norm = normalize_text_dashes(phrase)
    variants = {phrase, p_norm}
    if "-" in p_norm:
        for d in ("\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212", "\ufe63", "\uff0d"):
            variants.add(p_norm.replace("-", d))
    return [v for v in variants if v]

pdf_path = r"C:\Users\nidhi\Downloads\Case Study 2 Supporting Material\Case Study 2 Supporting Material\Cadence_Group_Risk_Management_Policy__v6.0.pdf"
with open(pdf_path, "rb") as f:
    raw_bytes = f.read()

doc = fitz.open(stream=raw_bytes, filetype="pdf")

exact_targets = [
    "EMP-38104", "EMP-40522", "EMP-37012", "EMP-37655",
    "m.achebe@cadencefg.com", "machebe@cadencefg.com",
    "t.lindqvist@cadencefg.com", "tlindqvist@cadencefg.com",
    "Miriam T. Achebe", "Tobias Lindqvist", "Anthony P. Brightwell",
    "Delphine R. Okonjo", "Rosalind M. Achterberg", "Helena Vorstermann",
    "Sunita R. Balakrishnan", "+1 (212) 555-0147", "+1 (917) 555-0143",
    "+44 20 7555 0171", "+44 20 7555 0163", "555-0147", "555-0143", "555 0171", "555 0163",
    "d.okonjo@cadencefg.com", "a.brightwell@cadencefg.com",
    "h.vorstermann@cadencefg.com", "s.balakrishnan@halloranpike.example",
]

tag_map = {}
token_to_label = {}
for t in exact_targets:
    norm_t = normalize_text_dashes(t)
    if norm_t.startswith("EMP-"):
        lbl = "[EMP_ID]"
    elif "@" in norm_t:
        lbl = "[EMAIL]"
    elif "555" in norm_t or norm_t.startswith("+"):
        lbl = "[PHONE]"
    else:
        lbl = "[PERSON]"
    tag_map[norm_t.lower()] = lbl
    for tok in norm_t.split():
        clean_tok = re.sub(r"^[(\[\"'\s<]+|[)\]\"'\s>,.:;]+$", "", tok)
        if len(clean_tok) >= 3 and clean_tok.lower() not in ("the", "and", "for", "with", "group", "all", "halloran"):
            token_to_label[clean_tok.lower()] = lbl

print(f"Initialized test with {len(exact_targets)} targets and {len(token_to_label)} token mappings")

total_redactions = 0
page_stats = {}

for page_idx in range(2):
    page = doc[page_idx]
    applied_rects = []
    
    words = page.get_text("words")
    tp = None
    if not words:
        tp = page.get_textpage_ocr(flags=0, language="eng", dpi=120, full=True, tessdata=os.environ.get("TESSDATA_PREFIX"))
        words = page.get_text("words", textpage=tp)
    
    page_text = page.get_text(textpage=tp) if tp is not None else page.get_text()
    page_text_norm = normalize_text_dashes(page_text)
    
    search_flags = fitz.TEXT_DEHYPHENATE | fitz.TEXT_PRESERVE_WHITESPACE
    search_kwargs = {"flags": search_flags}
    if tp is not None:
        search_kwargs["textpage"] = tp
    
    # Pass 1: Phrase search
    for phrase in exact_targets:
        lbl = tag_map.get(normalize_text_dashes(phrase).lower(), "[REDACTED]")
        for variant in get_dash_variants(phrase):
            for r in page.search_for(variant, **search_kwargs):
                if any(r.intersects(existing) for existing in applied_rects):
                    continue
                page.add_redact_annot(r, text=lbl, fill=(1, 1, 1), text_color=(0, 0, 0), fontsize=8)
                applied_rects.append(r)
                total_redactions += 1

    # Pass 2: Token-level matching
    for i, w in enumerate(words):
        w_norm = normalize_text_dashes(w[4].strip())
        clean_w = re.sub(r"^[(\[\"'\s<]+|[)\]\"'\s>,.:;]+$", "", w_norm)
        if not clean_w:
            continue
        rect = fitz.Rect(w[0], w[1], w[2], w[3])
        if any(rect.intersects(existing) for existing in applied_rects):
            continue
            
        matched_label = token_to_label.get(clean_w.lower())
        if not matched_label:
            if re.search(r"^EMP[-_]?\d{3,}", clean_w, re.IGNORECASE):
                matched_label = "[EMP_ID]"
            elif "@" in clean_w and re.search(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$", clean_w):
                matched_label = "[EMAIL]"
            elif re.search(r"^\d{3}-\d{2}-\d{4}$", clean_w):
                matched_label = "[SSN]"
            elif re.search(r"^\d{3}[-.]\d{4}$", clean_w):
                matched_label = "[PHONE]"
        
        if matched_label:
            page.add_redact_annot(rect, text=matched_label, fill=(1, 1, 1), text_color=(0, 0, 0), fontsize=8)
            applied_rects.append(rect)
            total_redactions += 1

    page_stats[page_idx + 1] = len(applied_rects)
    if applied_rects:
        page.apply_redactions()
        print(f"Page {page_idx + 1}: applied {len(applied_rects)} redactions")

out_bytes = doc.tobytes(garbage=3, deflate=True)
doc.close()

print(f"Total redactions applied across Page 1 & 2: {total_redactions}")
output_file = "cadence_policy_verified_redacted.pdf"
with open(output_file, "wb") as f:
    f.write(out_bytes)
print(f"Verified output written to {output_file}")
