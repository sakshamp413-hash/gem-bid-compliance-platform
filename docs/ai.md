# AI & Machine Learning Architecture

PRAMAAN utilizes a bounded, explainable, and multi-tier artificial intelligence architecture. AI in PRAMAAN is designed to solve genuinely unstructured data extraction and entity matching problems, while never acting as an unchecked legal authority.

---

## 1. Document Intelligence & OCR Pipeline

### 1.1 Dual-Engine OCR Strategy
1. **High-Speed Text-Layer Parsing (`pdfplumber`):**
   * Used for digitally created PDFs (the majority of contemporary GeM certificates).
   * Extracts text, tables, and bounding boxes (`bbox`) in under 200ms per page with zero GPU overhead.
2. **Layout-Aware Vision Model (`PaddleOCR`):**
   * Used when a scanned document or image-only PDF is detected.
   * Performs orientation detection, deskewing, binarization, and multilingual (English + Hindi) text and coordinate extraction.

### 1.2 Layout-Aware Structured Entity Extraction
Extracted text is mapped into typed per-document schemas:
* **GST Certificate:** Extracts GSTIN, Legal Name, Trade Name, Registration Date, Constitution of Business.
* **Udyam Certificate:** Extracts Udyam Registration Number, Enterprise Major Activity (Manufacturing/Services), Enterprise Type (Micro/Small/Medium).
* **PAN Card / Confirmation:** Extracts 10-character PAN, Father's Name / Legal Entity Name, Date of Incorporation.
* **Make-in-India Self-Declaration:** Extracts claimed local content percentage and verifies mathematical consistency with the Bill of Materials (BoM).

Every extracted field is recorded with:
$$\text{EntityRecord} = \{\text{key}, \text{value}, \text{confidence}, \text{page\_number}, \text{bbox: } (x_0, y_0, x_1, y_1)\}$$

---

## 2. Entity Resolution & Cross-Document Verification

### 2.1 Fuzzy Entity Matching Algorithm
Vendors frequently have minor syntactic differences in legal entity names across different statutory databases (e.g., *"CleanCorp Industrial Solutions Private Limited"* on MCA vs. *"CleanCorp Industrial Solutions Pvt Ltd"* on GSTIN).

PRAMAAN applies a domain-aware name matching pipeline:
1. **Normalization:** Strips legal entity suffixes (`Pvt Ltd`, `Private Limited`, `LLP`, `Inc`, `Co`) into canonical tokens.
2. **Token Sort Ratio (`rapidfuzz`):** Computes order-insensitive Levenshtein similarity:
   $$\text{Similarity}(S_1, S_2) = \frac{2 \cdot |S_1 \cap S_2|}{|S_1| + |S_2|}$$
3. **Threshold Gates:**
   * $\ge 0.90$: Match confirmed (`PASS`).
   * $0.75 - 0.89$: Flagged for human review (`FLAG_MANUAL_REVIEW`).
   * $< 0.75$: Discrepancy detected (`FAIL`).

---

## 3. Sovereign AI & Offline Fallback Architecture

To ensure the platform operates reliably in air-gapped government environments without cloud dependency:
* `LLM_PROVIDER=offline`: Executes pure Python regex, layout heuristics, and deterministic rule matchers.
* `LLM_PROVIDER=ollama`: Interfaces with locally hosted open-weight models (e.g., Llama-3.2-3B or Mistral-7B) running on on-premise hardware.
* `LLM_PROVIDER=openai`: Interfaces with cloud-compatible endpoints for development and testing.

AI assists by generating plain-language reasoning summaries and explanations. All final qualification statuses remain strictly governed by the rule engine and the human officer.
