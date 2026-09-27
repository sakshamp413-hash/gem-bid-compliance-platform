# Security Architecture & Controls

PRAMAAN is designed as public-sector digital infrastructure where data integrity, cryptographic non-repudiation, and sensitive bidder privacy are core engineering imperatives.

---

## 1. Cryptographic Document & PKI Verification

### 1.1 pyHanko PKI Verification Engine
Every uploaded PDF document (e.g., GST certificates, OEM authorizations, CA turnover letters) is inspected for embedded digital signatures conforming to CMS/PKCS#7 and CAdES/PAdES standards.
* **Digest Verification:** Validates that the byte range covered by the signature has not suffered bit-level corruption or alteration.
* **Certificate Chain Validation:** Validates the signer certificate up to an institutional root certificate (in demo mode, `storage/certs/demo_ca.pem`; in production, authorized DigiLocker / Controller of Certifying Authorities (CCA) roots).
* **Revocation & Expiry:** Asserts the signing timestamp against certificate validity windows.

### 1.2 Byte-Level PDF Tampering & Forgery Detection (`pikepdf`)
Fraudulent vendors frequently alter values (such as turnover figures or local content percentages) in previously signed documents using desktop PDF editors. PRAMAAN detects these forgeries through byte-level structural forensics:
1. **Incremental Update Analysis:** Counts incremental save sections in the PDF stream. Any update applied after the signature dictionary is parsed to determine whether it modified visual content or annotations outside permitted signature forms.
2. **Metadata vs. Stream Desynchronization:** Cross-references `/ModDate` inside the Document Information Dictionary with the embedded PKI cryptographic timestamp token.
3. **Producer & Tool Fingerprints:** Flags producer strings associated with cracked PDF manipulation tools or desktop image editors applied to statutory certificates.

---

## 2. Cryptographic Hash-Chained Audit Ledger

### 2.1 The Hashing Formulation
Audit log records are append-only. Each entry is chained to the preceding entry using SHA-256:
$$\text{Current Hash}_i = \text{SHA256}\left( \text{seq}_i \,\|\, \text{timestamp}_i \,\|\, \text{actor}_i \,\|\, \text{action}_i \,\|\, \text{entity}_i \,\|\, \text{payload\_hash}_i \,\|\, \text{Current Hash}_{i-1} \right)$$

* For the genesis record ($i = 0$), $\text{Current Hash}_{-1} = \text{0x000...000}$ (64 zeros).
* **Mathematical Break Detection:** The `/api/v1/audit/verify` endpoint recalculates the cryptographic chain sequentially from genesis to head. If any row has been modified, deleted, or inserted out of order, the calculated hash diverges immediately, pinpointing the exact corrupted sequence number.

---

## 3. Data Protection & Privacy Controls

### 3.1 PII Log Redaction
Public procurement documents contain sensitive personal and financial identifiers. PRAMAAN implements a central logging formatter that intercepts all log records and applies sanitizing regular expressions before persisting:
* **Income Tax PAN:** `[A-Z]{5}[0-9]{4}[A-Z]` -> Masked as `XXXXX1234X`
* **GSTIN:** `[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}` -> Masked as `27XXXXX1234X1ZX`
* **Bank Account Numbers:** Sequences of 9 to 18 digits preceded by account markers -> Masked as `XXXXXXXXXXXX5678`
* **Aadhaar Numbers:** 12-digit numeric sequences -> Permanently redacted to `XXXXXXXXXXXX`

### 3.2 Field-Level Encryption at Rest
All PAN, GSTIN, and Bank Account records are stored in the database using Fernet symmetric encryption (AES-128-CBC with HMAC authentication). Database dumps alone cannot yield readable tax or banking credentials without the external key.

---

## 4. Authentication, Authorization & RBAC
* **Session Tokens:** Stateless JWTs with a 60-minute expiry window, accompanied by 7-day refresh tokens.
* **Brute-Force Rate Limiting:** Auth endpoints enforce an in-memory sliding-window limiter capping login attempts at 20 requests per minute per IP address.
* **Role Separation:**
  * Officers can view bids, inspect evidence, flag anomalies, and record decisions.
  * Admins can configure rules, update policy thresholds, and manage users.
  * Auditors have strictly read-only access to submissions, reports, and cryptographic verification endpoints.
