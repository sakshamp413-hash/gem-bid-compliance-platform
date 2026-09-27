# Government Pilot & Departmental Onboarding Plan

This document outlines the operational roadmap for public sector procurement directorates, Central PSUs, and state procurement departments to pilot and onboard PRAMAAN.

---

## 1. Pilot Engagement Framework (90-Day Sandboxed Pilot)

```
[Day 1 - 15]                   [Day 16 - 45]                  [Day 46 - 75]                  [Day 76 - 90]
Architecture & Security Review  Historical Tender Benchmarking Parallel Evaluation            Final Review & Transition
• Network topology clearance   • Ingest 50-100 closed tenders • Live bids mirrored to PRAMAAN • Pilot report to CVC/CAG
• RBAC & officer directory     • Compare manual vs. PRAMAAN   • Officers use split-screen     • Readiness assessment
• Synthetic adapter dry-run    • Calibrate rule weights       • Time/accuracy delta logged   • Full rollout blueprint
```

---

## 2. Departmental Prerequisites & Data Requirements
To initiate a departmental pilot, the onboarded entity provides:
1. **Sample Historical Tender Dossiers:** 20 to 50 anonymized tender ATC PDFs and associated bidder submissions to validate domain-specific technical clauses.
2. **Designated Evaluation Officers:** 3 to 5 evaluating officers for user acceptance testing and feedback calibration.
3. **Infrastructure Mode Preference:**
   * **Option 1 (NIC / Government Private Cloud):** Deployed within the department's authorized VPC.
   * **Option 2 (Sovereign Managed Cloud):** Deployed on MeitY-empanelled cloud instances in India (AWS Mumbai / GCP Delhi).

---

## 3. SLA & Operational Commitments During Pilot
* **Availability:** 99.5% uptime during operational business hours.
* **Support Response:** Critical bug resolution within 4 business hours.
* **Security Clearance:** Compliance with CERT-In guidelines; zero persistent storage of unencrypted PII.
* **Human Primacy:** Reiteration that PRAMAAN operates strictly as a decision-support advisory system; sovereign officer authority remains absolute.
