# Compliance Engine & Rule Architecture

The PRAMAAN Compliance Engine evaluates bidder documents against statutory requirements and tender-specific criteria using an explainable, deterministic scoring framework.

---

## 1. Declarative Rule Architecture (`rules.yaml`)

Compliance rules are decoupled from program code and maintained as structured YAML configurations. This allows procurement officers and administrators to update threshold values, policy citations, and check weights when government procurement notifications are issued.

### 1.1 Structure of a Rule Definition
```yaml
- check_code: "STAT_GST_ACTIVE"
  category: "statutory"
  severity: "mandatory"       # mandatory | conditional | optional
  weight: 15.0                # Base score contribution
  title: "GSTIN Registration & Filing Status"
  description: "Verifies the vendor's GSTIN is active and returns are filed up to date."
  policy_citation: "GeM GTC Clause 3(i) & Central GST Act 2017"
  failure_action: "DISQUALIFY"
  conditions:
    - field: "gstin.status"
      operator: "EQUALS"
      expected: "Active"
    - field: "gstin.returns_filed"
      operator: "EQUALS"
      expected: true
```

---

## 2. Multi-Component Scoring Formulation

The overall compliance score (0.0 to 100.0) is calculated as a normalized weighted sum:

$$\text{Compliance Score} = \frac{\sum_{i=1}^{N} \left( W_i \cdot S_i \cdot C_i \right)}{\sum_{i=1}^{N} W_i} \times 100$$

Where:
* $W_i$: Normalized weight of rule $i$ (mandatory rules carry higher weights).
* $S_i$: Outcome score ($1.0$ for `PASS`, $0.5$ for `FLAG` / partial match, $0.0$ for `FAIL`).
* $C_i$: Extraction and verification confidence ($0.0 \le C_i \le 1.0$).

### 2.1 Hard Disqualification Overrides
A high statistical score is never allowed to override a mandatory legal disqualification. Regardless of whether the calculated score is $95/100$, the system automatically assigns `DISQUALIFY` if any of the following occur:
1. Active debarment/blacklisting detected on CVC or GeM registries.
2. Cryptographic signature invalidation or post-signing PDF tampering detected.
3. Inactive or cancelled statutory GSTIN/PAN.

---

## 3. Human-in-the-Loop Governance & Overrides

1. **System Recommends, Human Decides:**
   * Score $\ge 90.0$ + No Critical Flags $\to$ `QUALIFY`
   * Score $50.0 - 89.9$ OR Ambiguous Entities $\to$ `NEEDS_REVIEW`
   * Score $< 50.0$ OR Hard Failure $\to$ `DISQUALIFY`
2. **Mandatory Audit of Human Overrides:**
   * If an officer qualifies a bidder flagged as `NEEDS_REVIEW` or `DISQUALIFY`, the platform enforces a mandatory text input field requiring justification (e.g., *"Administrative waiver granted as per Circular No. 42"*).
   * The officer's ID, timestamp, original system score, and written justification are bundled into a cryptographic payload and committed to the hash-chained audit ledger.
