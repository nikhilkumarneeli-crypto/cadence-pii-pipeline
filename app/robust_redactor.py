"""Robust PDF redaction for Cadence PII Shield (digital AND image-only PDFs).

Why: Cadence_Group_Risk_Management_Policy__v6.0.pdf is a "Word -> picture" export:
every page is ONE JPEG plus a single-space text layer, so page.get_text()/search_for()
see nothing. Fix = OCR each page, redact the OCR word boxes (apply_redactions() also
blanks the scan pixels underneath), then re-OCR the output as a zero-leak check.

Public API
    redact_pdf_bytes(pdf_bytes, rules, literals)            -> (bytes, stats)   sequential
    redact_pdf_parallel(pdf_bytes, rules, literals, ...)    -> (bytes, stats)   multi-process
"""
from __future__ import annotations
import os
import re
from dataclasses import dataclass
from pathlib import Path
import pymupdf as fitz  # `import fitz` also works on older installs

# Ensure TESSDATA_PREFIX is configured on Windows
for p in [
    os.environ.get("TESSDATA_PREFIX"),
    r"C:\Program Files\Tesseract-OCR\tessdata",
    r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
    str(Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tessdata"),
]:
    if p and Path(p).exists():
        os.environ["TESSDATA_PREFIX"] = str(p)
        break

# ---------------- 1. Unicode normalisation (1:1 char map => offsets preserved) ----------------
_DASHES = "‐‑‒–—―−﹘﹣－"
_SPACES = "       "
_TRANS = {ord(c): "-" for c in _DASHES}
_TRANS.update({ord(c): " " for c in _SPACES})


def normalize(text: str) -> str:
    return text.translate(_TRANS)


@dataclass
class Rule:
    pattern: str
    label: str
    flags: int = re.I


FORBIDDEN_NAME_WORDS = {
    "diligence",
    "due",
    "partner",
    "partners",
    "vendor",
    "vendors",
    "group",
    "groups",
    "team",
    "teams",
    "tier",
    "category",
    "classification",
    "confidential",
    "internal",
    "external",
    "provider",
    "providers",
    "service",
    "services",
    "management",
    "governance",
    "compliance",
    "workflow",
    "workflows",
    "template",
    "templates",
    "questionnaire",
    "questionnaires",
    "assessment",
    "assessments",
    "training",
    "risk",
    "risks",
    "security",
    "quality",
    "owner",
    "owners",
    "reviewer",
    "reviewers",
    "lead",
    "leads",
    "contact",
    "contacts",
    "audit",
    "process",
    "processes",
    "integration",
    "requirement",
    "requirements",
    "rule",
    "rules",
    "stage",
    "stages",
    "attribute",
    "attributes",
    # Additional TPRM and business terminology
    "optiv",
    "cadence",
    "torii",
    "servpro",
    "stafven",
    "revpart",
    "marpart",
    "intven",
    "client",
    "clients",
    "business",
    "revenue",
    "marketing",
    "staffing",
    "international",
    "procurement",
    "finance",
    "legal",
    "third-party",
    "third",
    "party",
    "parties",
    "action",
    "actions",
    "function",
    "functions",
    "operation",
    "operations",
    "technology",
    "system",
    "systems",
    "application",
    "applications",
    "sla",
    "slas",
    "status",
    "control",
    "controls",
    "response",
    "responses",
    "score",
    "scores",
    "logic",
    "trigger",
    "triggers",
    "automation",
    "option",
    "options",
    "type",
    "types",
    "department",
    "division",
    "policy",
    "policies",
    "project",
    "scope",
    "document",
    "version",
    "draft",
    "final",
    "overview",
    "introduction",
    "summary",
    "table",
    "section",
    "appendix",
    "opportunity",
    "agreement",
    "contract",
    "email",
    "cloud",
    "authority",
    "incumbent",
    "secretary",
    "assessor",
    "auditor",
    "sponsor",
    "custodian",
    "delegate",
    "approval",
    "approver",
    "approvers",
}


def is_forbidden_name(val: str) -> bool:
    """Check if value or any constituent token is a common English noun/TPRM term."""
    if not val:
        return True
    norm = " ".join(val.lower().strip().split()).rstrip(".,;:")
    if norm in FORBIDDEN_NAME_WORDS:
        return True
    tokens = re.findall(r"[a-z0-9'\-]+", norm)
    if not tokens:
        return True
    return any(t in FORBIDDEN_NAME_WORDS for t in tokens)


GOVERNANCE_STOPWORDS = {
    "board risk committee", "board of directors", "audit committee",
    "remuneration committee", "group executive risk committee",
    "asset & liability committee", "asset and liability committee",
    "operational risk committee", "credit risk committee",
    "technology & cyber risk committee", "technology and cyber risk committee",
    "conduct & compliance committee", "conduct and compliance committee",
    "new product approval committee", "divisional risk committee",
    "divisional risk committees", "cadence financial group",
    "cadence financial group, inc.", "cadence capital markets",
    "cadence asset management", "cadence bank", "cadence financial",
    "group risk management policy", "risk management policy",
    "risk management", "enterprise risk framework", "enterprise risk",
    "internal audit", "three lines model", "first line", "second line", "third line",
    "first line of defence", "second line of defence", "third line of defence",
    "board risk", "wire transfer control policy", "document control",
    "version control", "policy queries", "halloran & pike", "halloran & pike llp",
}

EXECUTIVE_ROSTER = [
    "Miriam T. Achebe", "Miriam Achebe", "M. T. Achebe",
    "Tobias Lindqvist", "T. Lindqvist",
    "Anthony P. Brightwell", "Anthony Brightwell",
    "Delphine R. Okonjo", "Delphine Okonjo",
    "Rosalind M. Achterberg", "Rosalind Achterberg",
    "Desmond N. Quarshie", "Desmond Quarshie",
    "Beatrix S. Lindenau", "Beatrix Lindenau",
    "Eleanor R. Vasquez-Holt", "Eleanor Vasquez-Holt",
    "Helena Vorstermann", "H. Vorstermann",
    "Sunita R. Balakrishnan", "Sunita Balakrishnan",
    "Naomi K. Osadebe", "Naomi Osadebe", "N. K. Osadebe",
    "Caleb A. Whitfield", "Caleb Whitfield",
    "Yevgeni A. Sorokina", "Yevgeni Sorokina", "YevgeniA. Sorokina",
    "Babatunde O. Osei-Tutu", "Babatunde Osei-Tutu", "B. O. Osei-Tutu",
    "Priyanka S. Raghavan", "Priyanka Raghavan", "P. S. Raghavan",
    "Arvind K. Pillai", "Arvind Pillai",
    "Marta Szewczyk",
    "Sofia Marchetti-Lang", "Sofia Marchetti",
    "Fumiko L. Nakagawa", "Fumiko Nakagawa",
    "Harriet L. Okafor", "Harriet Okafor",
    "Devansh R. Kulkarni", "Devansh Kulkarni",
    "Lars-Erik Brannstrom",
    "Fatima Z. Qureshi", "Fatima Qureshi", "FatimaZ. Qureshi",
    "Denis Kowalczyk",
    "Rafael E. Duarte", "Rafael Duarte", "R. E. Duarte",
    "Ifeoma C. Adeyemi", "Ifeoma Adeyemi",
    "Yusuf O. Balogun", "Yusuf Balogun",
    "Grazyna Wieczorek",
    "Gregor Halvorsen",
    "Ananya V. Chatterjee", "Ananya Chatterjee", "A. V. Chatterjee",
    "Mireille Dubois-Kane", "Mireille Dubois",
    "Aiko Nakamura-Reed", "Aiko Nakamura",
    "Vikramaditya Rao", "Vikram Rao",
    "Sarah Jenkins",
    "Ananya Sharma",
    "Marcus Vance",
    # Cadence TPRM personnel
    "Daniela Figueroa",
    "Bridgett Gatewood",
    "KC Burney",
    "Jyoti Karwal",
    "Tamika Oliver",
    "Shimane Smith",
    "Chris Schmitz",
    "Chris Ott",
    "Rob Tilney",
    "Jonathan Szeto",
    "Marc Otani",
    "Dayo Seton",
    "Melisa Cardozo",
    "DK Koran",
    "Erik Hansen",
    "Siddharth Gaikwad",
    "Srinivas Teppa",
    "Nikhil Karkera",
]


def is_governance_term(val: str) -> bool:
    """Strictly filter out corporate bodies, governance committees, and framework titles."""
    if not val:
        return True
    if is_forbidden_name(val):
        return True
    norm = " ".join(val.lower().strip().split()).rstrip(".,;:")
    if norm in GOVERNANCE_STOPWORDS:
        return True
    for g in GOVERNANCE_STOPWORDS:
        if norm == g or (len(norm) >= 8 and (norm in g or g in norm)):
            return True
    tokens = set(re.findall(r"[a-z&]+", norm))
    gov_tokens = {
        "committee", "committees", "council", "board", "framework", "policy",
        "model", "portal", "department", "division", "divisions", "cadence",
        "governance", "management", "directors", "audit", "compliance",
        "remuneration", "lines", "line", "defence", "defense",
        "ned", "cro", "cfo", "ciso", "cco", "ceo", "coo", "cae", "gc",
    }
    if any(t in gov_tokens for t in tokens):
        return True
    return False


def is_valid_person_name(val: str) -> bool:
    """Strictly validate whether a candidate string is a real person name."""
    if not val:
        return False
    clean = val.strip().rstrip(".,;:")
    if is_forbidden_name(clean) or is_governance_term(clean):
        return False
    if re.search(r"[\d_]", clean):
        return False
    if clean.count(".") > 2:
        return False
    if clean in EXECUTIVE_ROSTER or any(clean.casefold() == ex.casefold() for ex in EXECUTIVE_ROSTER):
        return True
    parts = clean.split()
    if not 2 <= len(parts) <= 5:
        return False
    for p in parts:
        p_clean = p.rstrip(".,;:")
        if not p_clean:
            return False
        if p_clean.lower() in FORBIDDEN_NAME_WORDS:
            return False
        if not p_clean[0].isupper():
            return False
        if len(p_clean) > 2 and p_clean.isupper():
            return False
        if not re.match(r"^[A-Z][a-zA-Z'\-\.]*$", p_clean):
            return False
    return True


def expand_name_span(text: str, start: int, end: int) -> tuple[int, int, str]:
    """Greedily expands name span across middle initials and multi-part surnames."""
    pre = text[:start].rstrip()
    title_m = re.search(r'\b(Dr|Mr|Mrs|Ms|Prof)\.?$', pre)
    if title_m:
        start = title_m.start()

    cur_end = end
    while cur_end < len(text):
        remainder = text[cur_end:]
        m = re.match(r'^([ \t]+)([A-Z]\.?|[A-Z][a-zA-Z\u2019\'\-]+)(?=[,;.!?\s\(\)\[\]]|$)', remainder)
        if not m:
            break
        token = m.group(2)
        if (
            token.lower() in FORBIDDEN_NAME_WORDS
            or is_forbidden_name(token)
            or is_governance_term(token)
        ):
            break
        cur_end += m.end()

    val = text[start:cur_end].strip()
    return start, cur_end, val


_TOK = r"(?:[A-Z][A-Za-z'’\-]+|[A-Z]\.)"
_ROLE_LABEL_PREFIXES = (
    r"policy\s+owner|policy\s+author|legal\s+reviewer|privacy\s+reviewer|approval\s+authority|"
    r"chaired\s+by|incumbent|prepared\s+by|approved\s+by|submitted\s+by|reported\s+by|"
    r"reviewed\s+by|attested\s+by|signatory|contact\s+person|lead\s+reviewer|chief\s+reviewer|"
    r"committee\s+chair|chairperson|peer\s+reviewer|qa\s+reviewer"
)
_ROLE_LABEL_PATTERN_STR = (
    rf"(?i:\b(?:{_ROLE_LABEL_PREFIXES})\b)\s*[:\-]\s*"
    r"([A-Z][a-z]+(?:\s+[A-Z]\.?)*(?:\s+[A-Z][a-z]+(?:-[A-Z][a-z]+)?)+)"
)

DEFAULT_RULES = [
    Rule(r"\bEMP-\d{3,8}\b", "[EMP_ID]"),
    Rule(r"\bDIR-\d{3,8}\b", "[EMP_ID]"),
    Rule(r"\b[A-Za-z0-9._%+-]+(?:\s*@\s*)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[EMAIL]"),
    Rule(r"(?<!\d)\d{3}-\d{2}-\d{4}(?!\d)", "[SSN]"),
    # phone: separators must NOT span newlines (they would swallow neighbouring table cells)
    Rule(r"(?<![\w-])(?:\+\d{1,3}[ \t.\-]?)?\(?\d{2,4}\)?[ \t.\-]\d{3,4}[ \t.\-]\d{4}(?!\d)", "[PHONE]"),
    # phone wrapped across lines: "+44 20" / "+1 (212)" / "+1" ...
    Rule(r"(?<![\w])\+\d{1,3}(?:[ \t]*\(?\d{2,4}\)?)?(?![\d-])", "[PHONE]"),
    # ... and its tail on its own line: "7555 0171" / "555-0147"
    Rule(r"^\(?\d{2,4}\)?[ \-]?\d{3,4}[ \-]\d{4}$|^\d{3,4}[ \-]\d{4}$", "[PHONE]", re.I | re.M),
    Rule(r"\b[A-Z]{5}\d{4}[A-Z]\b", "[GOV_ID]", 0),
    # 2-3 capitalised tokens (initials allowed) directly before an employee or director ID = a person's name
    Rule(_TOK + r"(?:[ \t]+" + _TOK + r"){1,2}(?=[ \t]*\(?(?:EMP|DIR)-\d)", "[PERSON]", 0),
    # role context name rule
    Rule(_ROLE_LABEL_PATTERN_STR, "[PERSON]", 0),
]

OCR_DPI = 300
MIN_TEXT_WORDS = 5    # fewer real words than this => page is image-only -> OCR

# Words that mean "role / committee / org", never a person (filters NER + heuristic false hits)
_NOT_NAME = set("""board risk committee cttee group chief officer head enterprise framework policy appetite
counsel general director financial cadence management executive internal audit credit market liquidity
operational compliance technology cyber conduct data privacy model climate third-party business continuity
resilience remuneration asset liability new product approval independent non-executive ned version appendix
section regulatory senior legal finance treasury security information governance assurance standard procedure
exception exceptions register incident loss event reporting escalation rcsa kri owner author reviewer
authority secretary chair chairman vice president manager lead critical high medium low material non wherea
whereas""".split()) | FORBIDDEN_NAME_WORDS


def _person_ok(txt: str) -> bool:
    if not txt or "@" in txt or any(c.isdigit() for c in txt):
        return False
    if is_forbidden_name(txt) or is_governance_term(txt):
        return False
    parts = txt.split()
    if not 2 <= len(parts) <= 5 or any(w.endswith("-") for w in parts):
        return False                                   # not a name: too long / cut-off token
    toks = re.findall(r"[A-Za-z][A-Za-z'\u2019\-]*", txt)
    if not toks or any(t.lower() in _NOT_NAME or t.lower() in FORBIDDEN_NAME_WORDS for t in toks):
        return False
    return is_valid_person_name(txt)


# ---------------- 2. Word extraction (native text layer, OCR fallback) ----------------
def _page_words(page: fitz.Page):
    """-> (words, used_ocr); words = [(x0,y0,x1,y1,text,block,line,wno), ...] in page coords."""
    words = [w for w in page.get_text("words", sort=True) if w[4].strip()]
    if len(words) >= MIN_TEXT_WORDS:
        return words, False
    tess_path = os.environ.get("TESSDATA_PREFIX")
    ocr_kwargs = {"dpi": OCR_DPI, "full": True, "language": "eng"}
    if tess_path:
        ocr_kwargs["tessdata"] = tess_path
    tp = page.get_textpage_ocr(**ocr_kwargs)
    words = [w for w in page.get_text("words", textpage=tp, sort=True) if w[4].strip()]
    return words, True


def _tokens(words):
    parts, spans, pos, prev = [], [], 0, None
    for w in words:
        key = (w[5], w[6])
        if parts:
            parts.append(" " if key == prev else "\n")
            pos += 1
        tok = normalize(w[4])
        spans.append((pos, pos + len(tok), fitz.Rect(w[:4])))
        parts.append(tok)
        pos += len(tok)
        prev = key
    return "".join(parts), spans


def _merge_line_rects(rects):
    rects = sorted(rects, key=lambda r: (round(r.y0 / 3), r.x0))
    out, cur = [], fitz.Rect(rects[0])
    for r in rects[1:]:
        if abs((r.y0 + r.y1) / 2 - (cur.y0 + cur.y1) / 2) < cur.height * 0.6:
            cur |= r
        else:
            out.append(cur); cur = fitz.Rect(r)
    out.append(cur)
    return out


# ---------------- 3. Person names: spaCy NER (optional) + EMP-ID heuristic ----------------
_NLP = None


def _get_nlp():
    global _NLP
    if _NLP is None:
        _NLP = False
        try:
            import spacy
            for m in ("en_core_web_lg", "en_core_web_md", "en_core_web_sm"):
                try:
                    _NLP = spacy.load(m, disable=["lemmatizer", "parser", "tagger", "attribute_ruler"])
                    break
                except Exception:
                    continue
        except Exception:
            pass
    return _NLP


def _ner_person_spans(text):
    """PERSON spans as (start, end) offsets into `text`. NER runs per line so a name can't
    swallow the first word of the next table cell."""
    nlp = _get_nlp()
    if not nlp:
        return []
    lines, offs, pos = [], [], 0
    for ln in text.split("\n"):
        lines.append(ln); offs.append(pos); pos += len(ln) + 1
    out = []
    for doc, off in zip(nlp.pipe(lines), offs):
        for ent in doc.ents:
            t = ent.text.strip()
            if ent.label_ == "PERSON" and _person_ok(t) and not is_governance_term(t):
                st = off + ent.start_char
                en = off + ent.end_char
                est, een, eval_ = expand_name_span(text, st, en)
                if not is_governance_term(eval_) and _person_ok(eval_):
                    out.append((est, een))
    return out


def collect_names(text: str, rules=DEFAULT_RULES):
    """Person names found on one page (NER + heuristic rules labelled [PERSON] + executive roster)."""
    names = set()
    for a, b in _ner_person_spans(text):
        ea, eb, eval_ = expand_name_span(text, a, b)
        if not is_governance_term(eval_) and _person_ok(eval_):
            names.add(eval_)
    for r in rules:
        if r.label == "[PERSON]":
            for m in re.finditer(r.pattern, text, r.flags):
                ms, me = (m.start(1), m.end(1)) if m.lastindex and m.lastindex >= 1 else (m.start(), m.end())
                ea, eb, eval_ = expand_name_span(text, ms, me)
                if not is_governance_term(eval_) and _person_ok(eval_):
                    names.add(eval_)
    for exec_name in EXECUTIVE_ROSTER:
        if re.search(rf"\b{re.escape(exec_name)}\b", text, re.I):
            names.add(exec_name)
    return {re.sub(r"\s+", " ", n).strip().rstrip(".,;:!?)]}>(\"'") for n in names if len(n) >= 4 and _person_ok(n) and not is_governance_term(n)}


def name_literals(names):
    """Whole names + optional middle-initial drop (e.g. 'Miriam Achebe' for 'Miriam T. Achebe').
    NEVER map isolated single surnames or first names alone (e.g. 'Achebe' alone),
    which causes orphaned surname redactions and false hits."""
    lits = {}
    for n in names:
        n = n.strip().rstrip(".,;:!?)]}>(\"'")
        if not n or is_governance_term(n):
            continue
        lits[n] = "[PERSON]"
        parts = n.split()
        if len(parts) == 3 and (len(parts[1]) <= 2 or parts[1].endswith(".")):
            no_mid = f"{parts[0]} {parts[2]}"
            if not is_governance_term(no_mid):
                lits[no_mid] = "[PERSON]"
    return lits


# ---------------- 4. Matching ----------------
def _literal_pattern(lit: str):
    lit = lit.strip().rstrip(".,;:!?)]}>(\"'")
    parts = lit.split()
    escaped_parts = []
    for p in parts:
        if "@" in p:
            ep = re.sub(r"\s*@\s*", r"\\s*@\\s*", re.escape(p))
            escaped_parts.append(ep)
        else:
            escaped_parts.append(re.escape(p))
    core = r"\s+".join(escaped_parts)
    pre = r"\b" if lit[0].isalnum() else ""
    post = r"\b" if lit[-1].isalnum() else ""
    return re.compile(pre + core + post, re.I)


def find_hits(words, rules, literals=None, ner=True):
    """-> [(rect, label)] from regex rules, detector literals, executive roster, and NER."""
    text, spans = _tokens(words)
    matches = []
    for r in rules:
        for m in re.finditer(r.pattern, text, r.flags):
            ms, me = (m.start(1), m.end(1)) if m.lastindex and m.lastindex >= 1 and r.label == "[PERSON]" else (m.start(), m.end())
            val = text[ms:me].strip()
            if r.label == "[PERSON]":
                if is_governance_term(val) or not _person_ok(val):
                    continue
                ems, eme, eval_ = expand_name_span(text, ms, me)
                if is_governance_term(eval_) or not _person_ok(eval_):
                    continue
                ms, me = ems, eme
            elif r.label == "[EMAIL]":
                clean_e = val.rstrip(".,;:!?)]}>(\"'")
                me = ms + len(clean_e)
            matches.append((ms, me, r.label))

    for lit, label in (literals or {}).items():
        lit = normalize(lit).strip().rstrip(".,;:!?)]}>(\"'")
        if len(lit) >= 3:
            if label == "[PERSON]" and is_governance_term(lit):
                continue
            for m in _literal_pattern(lit).finditer(text):
                m_val = text[m.start():m.end()]
                if label == "[PERSON]" and is_governance_term(m_val):
                    continue
                matches.append((m.start(), m.end(), label))

    for exec_name in EXECUTIVE_ROSTER:
        for m in re.finditer(rf"\b{re.escape(exec_name)}\b", text, re.I):
            val = text[m.start():m.end()]
            if not is_governance_term(val):
                matches.append((m.start(), m.end(), "[PERSON]"))

    if ner:
        for a, b in _ner_person_spans(text):
            ea, eb, eval_ = expand_name_span(text, a, b)
            if not is_governance_term(eval_) and _person_ok(eval_):
                matches.append((ea, eb, "[PERSON]"))

    hits = []
    for ms, me, label in matches:
        rs = [r for (s, e, r) in spans if s < me and e > ms]
        if rs:
            hits += [(r, label) for r in _merge_line_rects(rs)]
    hits.sort(key=lambda h: -h[0].get_area())          # drop boxes mostly covered by a bigger one
    kept = []
    for r, lab in hits:
        if not any(k.contains(r) or (k & r).get_area() > 0.6 * r.get_area() for k, _ in kept):
            kept.append((r, lab))
    return kept


# ---------------- 5. Annotate / apply ----------------
def _fit_fontsize(label, width, max_fs=8.0, min_fs=4.0):
    fs = max_fs
    while fs > min_fs and fitz.get_text_length(label, fontname="helv", fontsize=fs) > width - 1:
        fs -= 0.5
    return fs


def _add_annot(page, rect, label):
    r = fitz.Rect(rect) + (-1.5, -1.0, 1.5, 1.0)       # OCR boxes are tight: pad
    fs = _fit_fontsize(label, r.width)
    fits = fitz.get_text_length(label, fontname="helv", fontsize=fs) <= r.width
    page.add_redact_annot(r, text=label if fits else "", fontname="helv", fontsize=fs,
                          fill=(1, 1, 1), text_color=(0, 0, 0),
                          align=fitz.TEXT_ALIGN_CENTER, cross_out=False)


def _empty_stats(n):
    return {"pages": n, "redactions": 0, "per_page": {}, "ocr_pages": [], "leaks": []}


def _verify(out_bytes, rules, stats):
    chk = fitz.open(stream=out_bytes, filetype="pdf")
    try:
        for page in chk:
            words, _ = _page_words(page)
            text, _sp = _tokens(words)
            for r in rules:
                if r.label == "[PERSON]":
                    continue                              # names: heuristic, not a leak signal
                for m in re.finditer(r.pattern, text, r.flags):
                    stats["leaks"].append((page.number + 1, m.group(0)))
    finally:
        chk.close()


def redact_pdf_bytes(pdf_bytes: bytes, rules=DEFAULT_RULES, literals=None, verify=True,
                     require_hits=True, pre_words=None, propagate_names=True):
    """-> (bytes, stats). Raises instead of silently returning an untouched PDF.
    pre_words: optional per-page [(words, used_ocr)] to skip OCR (used by the parallel driver)."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    stats = _empty_stats(len(doc))
    try:
        if pre_words is None:
            pre_words = [_page_words(p) for p in doc]
        if propagate_names:
            names = set()
            for words, _ in pre_words:
                names |= collect_names(_tokens(words)[0], rules)
            literals = {**name_literals(names), **(literals or {})}
        for page, (words, used_ocr) in zip(doc, pre_words):
            if used_ocr:
                stats["ocr_pages"].append(page.number + 1)
            hits = find_hits(words, rules, literals)
            for rect, label in hits:
                _add_annot(page, rect, label)
            if hits:   # IMAGE_PIXELS blanks the pixels of the page scan under each box
                page.apply_redactions(images=fitz.PDF_REDACT_IMAGE_PIXELS,
                                      graphics=fitz.PDF_REDACT_LINE_ART_NONE)
                stats["per_page"][page.number + 1] = len(hits)
                stats["redactions"] += len(hits)
        if stats["redactions"] == 0 and require_hits:
            raise RuntimeError(f"0 redactions on {stats['pages']} pages "
                               f"(OCR used on {len(stats['ocr_pages'])}) - refusing to "
                               "export an unmodified PDF.")
        out = doc.tobytes(garbage=3, deflate=True)
    finally:
        doc.close()
    if verify:
        _verify(out, rules, stats)
    return out, stats


# ---------------- 6. Parallel driver (OCR ~6 s/page => spread pages over CPU cores) ----------------
def _init_worker():
    import os
    from pathlib import Path
    os.environ["OMP_THREAD_LIMIT"] = "1"               # one tesseract thread per process
    for p in [
        os.environ.get("TESSDATA_PREFIX"),
        r"C:\Program Files\Tesseract-OCR\tessdata",
        r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
        str(Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tessdata"),
    ]:
        if p and Path(p).exists():
            os.environ["TESSDATA_PREFIX"] = str(p)
            break


def _ocr_worker(chunk_bytes):
    d = fitz.open(stream=chunk_bytes, filetype="pdf")
    try:
        return [_page_words(p) for p in d]
    finally:
        d.close()


def _redact_worker(args):
    chunk_bytes, pre_words, rules, literals = args
    return redact_pdf_bytes(chunk_bytes, rules, literals, verify=True, require_hits=False,
                            pre_words=pre_words, propagate_names=False)


def redact_pdf_parallel(pdf_bytes: bytes, rules=DEFAULT_RULES, literals=None,
                        workers=None, progress=None):
    """Same result as redact_pdf_bytes(). progress(done_units, total_units) reports
    3 equal stages: OCR, redact, verify (verify runs inside the redact workers)."""
    import os
    from pathlib import Path
    from concurrent.futures import ProcessPoolExecutor, as_completed

    for p in [
        os.environ.get("TESSDATA_PREFIX"),
        r"C:\Program Files\Tesseract-OCR\tessdata",
        r"C:\Program Files (x86)\Tesseract-OCR\tessdata",
        str(Path.home() / "AppData" / "Local" / "Programs" / "Tesseract-OCR" / "tessdata"),
    ]:
        if p and Path(p).exists():
            os.environ["TESSDATA_PREFIX"] = str(p)
            break

    src = fitz.open(stream=pdf_bytes, filetype="pdf")
    n = len(src)
    workers = max(1, min(workers or (os.cpu_count() or 2), n))
    if workers == 1 or n < 4:
        out, st = redact_pdf_bytes(pdf_bytes, rules, literals)
        if progress: progress(n, n)
        return out, st
    size = max(1, -(-n // (workers * 2)))
    chunks = []
    for a in range(0, n, size):
        b = min(a + size, n)
        sub = fitz.open(); sub.insert_pdf(src, from_page=a, to_page=b - 1)
        chunks.append((a, sub.tobytes(garbage=3, deflate=True), b - a)); sub.close()
    src.close()
    total = n * 2                                       # OCR pass + (redact+verify) pass

    done, words_by_chunk = 0, {}
    with ProcessPoolExecutor(max_workers=workers, initializer=_init_worker) as ex:
        # phase 1: OCR every page
        futs = {ex.submit(_ocr_worker, b): (a, cnt) for a, b, cnt in chunks}
        for f in as_completed(futs):
            a, cnt = futs[f]; words_by_chunk[a] = f.result()
            done += cnt
            if progress: progress(done, total)
        # document-wide person names -> literals applied on every page
        names = set()
        for a, _b, _c in chunks:
            for words, _ in words_by_chunk[a]:
                names |= collect_names(_tokens(words)[0], rules)
        lits = {**name_literals(names), **(literals or {})}
        # phase 2: redact + verify
        results = {}
        futs = {ex.submit(_redact_worker, (b, words_by_chunk[a], rules, lits)): (a, cnt)
                for a, b, cnt in chunks}
        for f in as_completed(futs):
            a, cnt = futs[f]; results[a] = f.result()
            done += cnt
            if progress: progress(done, total)

    merged = fitz.open()
    stats = _empty_stats(n)
    for a, _b, _c in chunks:
        b, st = results[a]
        part = fitz.open(stream=b, filetype="pdf"); merged.insert_pdf(part); part.close()
        stats["redactions"] += st["redactions"]
        stats["per_page"].update({a + k: v for k, v in st["per_page"].items()})
        stats["ocr_pages"] += [a + k for k in st["ocr_pages"]]
        stats["leaks"] += [(a + pg, t) for pg, t in st["leaks"]]
    out = merged.tobytes(garbage=3, deflate=True); merged.close()
    if stats["redactions"] == 0:
        raise RuntimeError(f"0 redactions on {n} pages - refusing to export an unmodified PDF.")
    return out, stats
