# Confidentiality & Data Protection Governance

**Project:** Cadence Financial Group — Case Study 2: Text Analysis & PII Detection  
**Role:** Member 3 (PowerPoint PPTX Extraction & Structure Retention Metric)  
**Classification:** Internal – Confidential  

---

## 1. Governance Principles & Strict Local Processing

The Cadence Organizational Reference Pack (`Cadence_Financial_Group_Organizational_Pack.pptx`) contains corporate organizational structures, synthetic employee profiles, corporate email addresses, and direct contact numbers. Under Cadence Financial Group's risk management standards, all assets must be treated as confidential.

Member 3 strictly enforces the following data protection guardrails:

1. **100% Air-Gapped Local Execution:**  
   All PPTX parsing, layout reconstruction, OCR adapter invocations, and structure metrics execute strictly on local machine hardware. No data ever leaves the local environment.

2. **Zero External API / Cloud Service Transmission:**  
   - No remote LLM or external AI API calls are used for extraction.
   - No cloud-based PPTX parsing services are utilized.
   - No online OCR services (e.g., cloud vision APIs) are called; only local Tesseract OCR or local Member 2 adapters are permitted.

3. **No Public Repository Publication:**  
   Source code, test data, and outputs are strictly maintained within local workspaces and private project drives. Public GitHub/GitLab pushes are prohibited.

4. **Synthetic Data Separation:**  
   All automated unit tests run against clean synthetic datasets generated in `test_data/pptx/`. Real personal identifiers are strictly absent from source code, commit history, and technical documentation.

5. **Clean Pipeline Interfaces:**  
   Extracted JSON outputs preserve provenance and spatial context while remaining ready for Member 4's on-premise PII classification engine and Member 5's pseudonymization/redaction engine without exposing raw data to untrusted endpoints.

---

## 2. Technical Safeguards Implemented

| Threat / Risk | Safeguard Implemented in Member 3 Engine |
|---|---|
| Accidental upload of PPTX | Purely offline Python libraries (`python-pptx`, `Pillow`) |
| Unencrypted cloud OCR leak | Offline local OCR adapter (`pytesseract` / Member 2 local hook) |
| Hardcoded secrets / credentials | Zero credentials required; zero environment tokens stored |
| Git leakage of confidential pack | Configured `.gitignore` rules and local evaluation paths |
| Context corruption leading to PII miss | Deterministic 2D spatial clustering keeps related PII together |
