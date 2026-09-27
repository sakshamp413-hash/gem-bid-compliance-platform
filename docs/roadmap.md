# Technical & Operational Roadmap (3 / 6 / 12 Months)

This document specifies the technical milestones for scaling PRAMAAN from the Smart India Hackathon prototype to a national procurement intelligence utility.

---

## 1. Phase 1: MVP & Sandboxed Pilot (Months 1–3)
* **Milestone 1.1:** Finalize automated clause segmentation for standard GeM Additional Terms & Conditions (ATC) documents.
* **Milestone 1.2:** Deploy pilot instance for a designated PSU procurement department (e.g., Oil & Gas / Power sector).
* **Milestone 1.3:** Calibrate deterministic YAML rule engine against 200 real-world historical tenders.
* **Milestone 1.4:** Conduct end-to-end user testing with 15 evaluating officers; measure reduction in evaluation turnaround time.

---

## 2. Phase 2: Live Integrations & Ecosystem Scaling (Months 4–6)
* **Milestone 2.1:** Onboard to official API Setu sandbox; replace mock portal stubs with mutual-TLS authenticated connections to GSTN, ITD (PAN), and MCA21.
* **Milestone 2.2:** Launch Vendor Self-Service Pre-Check portal, allowing registered MSMEs to evaluate bid compliance readiness prior to formal submission.
* **Milestone 2.3:** Transition background worker architecture to distributed Celery/Redis queue for high-concurrency scanned OCR processing via PaddleOCR clusters.
* **Milestone 2.4:** Expand multilingual capability to support Hindi and 3 regional languages (Tamil, Marathi, Bengali) across checklist interfaces.

---

## 3. Phase 3: National Infrastructure & Federation (Months 7–12)
* **Milestone 3.1:** Deploy federated sovereign nodes across Central and State government procurement departments with centralized policy synchronization.
* **Milestone 3.2:** Deploy dedicated Auditor Portal nodes for independent oversight bodies (CAG, CVC) featuring real-time ledger verification and anomaly alerts.
* **Milestone 3.3:** Integrate cross-tender collusion intelligence to detect shell company networks operating across multiple ministries and states.
* **Milestone 3.4:** Achieve full CERT-In security audit certification and formal empanelment on the GeM portal.
