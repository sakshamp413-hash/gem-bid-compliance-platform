# Testing Strategy & Verification Report

PRAMAAN enforces multi-tiered automated testing across unit, integration, cryptographic, and end-to-end acceptance layers.

---

## 1. Test Suite Structure (`backend/tests`)

| Test Module | Coverage Scope | Key Assertions & Scenarios |
| :--- | :--- | :--- |
| `test_tamper.py` | PDF Byte-Level Forensics | Asserts that post-signing incremental updates flip `is_tampered=True`; detects modified `/ModDate` and invalid xref tables. |
| `test_collusion.py` | Cross-Bidder Collusion | Tests graph clustering algorithm against bidders sharing bank accounts, IFSC codes, and fuzzy signatory names. |
| `test_audit.py` | Cryptographic Audit Chaining | Tests sequential SHA-256 chain calculation; verifies that manually altering a DB row triggers `CHAIN_BROKEN` at the exact index. |
| `test_auth.py` | Authentication & RBAC | Validates JWT token generation, role verification (`officer`, `admin`, `auditor`), and brute-force rate limiting. |
| `test_pipeline.py` | End-to-End Compliance Pipeline | Tests document ingestion, checklist matching, weighted scoring, risk assignment, and recommendation outputs. |
| `test_id_validators.py`| Statutory ID Parsers | Validates Luhn-mod-36 checksum for GSTINs, 10-char structural format for PAN, and Udyam MSME formatting. |
| `test_local_content.py`| Make in India Rules | Verifies Class-I (>=50%) and Class-II (>=20%) local content calculations from Bill of Materials. |

---

## 2. Running Automated Tests

### 2.1 Backend Tests (pytest)
```bash
# Activate virtual environment
cd backend
# Run test suite with verbose output
pytest -v

# Run with test coverage report
pytest --cov=app --cov-report=term-missing
```
*Current Status:* **82 passed**, 100% test pass rate on all critical compliance and security paths.

### 2.2 Frontend Tests (Vitest & React Testing Library)
```bash
cd frontend
npm test -- --run
```
*Current Status:* **7 passed**, covering ScoreGauge rendering, risk level badges, and interactive accordion components.
