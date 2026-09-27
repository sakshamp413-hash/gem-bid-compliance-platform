# PRAMAAN 5-Minute Grand Finale Live Demonstration Script

This document provides the word-for-word spoken presentation track, synchronized actions, and fallback contingency protocols for presenting PRAMAAN to an executive jury.

---

## 1. Demo Execution Timeline

```
[0:00 - 0:30]               [0:30 - 1:15]               [1:15 - 2:15]               [2:15 - 3:15]               [3:15 - 4:15]               [4:15 - 5:00]
Problem & Core Hook         Tender Intelligence         Clean vs. Borderline MSME   Forensic Integrity & Collusion Sovereign Adjudication      Audit Verification & Close
• MSME technical loss       • Ingest Pump Tender        • CleanCorp (95.0 Qualify)  • FraudFillers (Tamper/Bad PKI)• Officer override & waiver • SHA-256 chain verification
• Officer document deluge   • Extract criteria checklist• Borderline (87.5 Review)  • FrontRunner + QuickSpares  • Mandatory typed justification• Tamper detection & call to action
```

---

## 2. Word-for-Word Script & Synchronized UI Actions

### [0:00 – 0:30] The Real Procurement Crisis
* **Presenter:**
  > *“Respected jury members, in public procurement today, a technically capable Indian MSME can manufacture world-class industrial equipment, yet still face technical disqualification simply because one tax certificate had a minor typographical discrepancy or expired three days prior to evaluation. At the same time, evaluating officers face mountains of PDFs under statutory deadlines, unable to detect when two competing bidders share the same bank account. PRAMAAN solves both sides of this crisis. Let’s look at the live platform.”*
* **Operator:** Screen shows PRAMAAN landing page. Demonstrates responsive layout, clean institutional branding, and active user session as `officer@gem.gov.in`.

### [0:30 – 1:15] Tender Intelligence & Ingestion
* **Presenter:**
  > *“We begin with Tender GeM/2026/B/1234567 for the 'Supply of Industrial Submersible Pumps'. Instead of an evaluating officer spending hours reading through the Additional Terms and Conditions, PRAMAAN parses the document into structured, machine-verifiable criteria: 5 years experience, active GST, Class-I local content, and OEM authorization. Everything is categorized and mapped to versioned procurement rules.”*
* **Operator:** Clicks into Tender Details. Expands the Compliance Checklist accordion, showing extracted requirements and statutory references.

### [1:15 – 2:15] Clean Bidder vs. Borderline MSME
* **Presenter:**
  > *“Now let’s evaluate our bidders. We open CleanCorp Industrial Solutions. The score gauge shows 95.0 — Low Risk, Qualify. Every statutory check passes. Notice the split-screen viewer: clicking on the GST check immediately opens the certificate, highlights the extracted GSTIN in green, and confirms the digital signature is cryptographically valid.*  
  > *Now, let’s open Borderline Traders. Their score drops to 87.5 — Needs Review. PRAMAAN instantly flags two issues: their Q3 GST return is missing, and there is an 82% fuzzy match discrepancy between their PAN name and Udyam certificate. The officer does not have to hunt for this; it is highlighted directly on page 2.”*
* **Operator:** Opens CleanCorp, clicks on GST check to show split-screen PDF with green highlight. Then opens Borderline Traders, displaying the amber status and highlighted name discrepancy.

### [2:15 – 3:15] Forensic Integrity & Collusion Intelligence
* **Presenter:**
  > *“Now witness the integrity engine. We select FraudFillers. The score crashes to 25.0 — Disqualify. Look at the red security banner: pikepdf and pyHanko have detected an invalid PKI signature and post-signing PDF stream tampering. Someone manually altered the Make-in-India percentage from 25% to 85% after the certificate was signed.*  
  > *Next, look at FrontRunner Pumps and QuickSpares Trading. Individually, both appear qualified with scores above 90. But look at our Collusion Intelligence Panel: PRAMAAN cross-references the entire bid batch and flags a critical anomaly — both bidders share the exact same HDFC bank account and authorized signatory. That is an active bid-rigging ring caught before commercial bid opening.”*
* **Operator:** Opens FraudFillers, zooms into the red tamper banner. Navigates to the Cross-Bidder Collusion panel, showing the detected bipartite cluster between FrontRunner and QuickSpares.

### [3:15 – 4:15] Sovereign Human Adjudication
* **Presenter:**
  > *“Notice what PRAMAAN did NOT do: it did not automatically disqualify anyone. AI assists; the sovereign officer decides. Returning to Borderline Traders, the officer determines that the name mismatch is a known clerical abbreviation. The officer selects 'Grant Conditional Waiver', enters the mandatory justification text, and clicks Record Decision. The override is preserved with complete attribution.”*
* **Operator:** Returns to Borderline Traders, selects 'Grant Conditional Waiver', types *"Clerical abbreviation verified against MCA Master Data; approved under Circular 12"*, and clicks submit.

### [4:15 – 5:00] Cryptographic Audit Verification & Close
* **Presenter:**
  > *“Finally, how do we prove this to the Comptroller and Auditor General? We switch to the Auditor Portal. Every action, extraction, and override is an immutable block in our SHA-256 hash-chained audit ledger. Let’s click 'Verify Ledger Integrity'. The system recomputes the chain from genesis to head in real-time: STATUS: INTACT. If any administrator were to alter a single record in the database, the system immediately flags the broken block index.*  
  > *PRAMAAN turns public procurement from an opaque, stressful paper battle into a transparent, secure, and auditable public digital good. Understand the tender. Verify the bid. Prove the decision. Thank you.”*
* **Operator:** Switches to Auditor view, clicks 'Verify Ledger Integrity', displaying the animated green INTACT verification badge.

---

## 3. Demo Failure Modes & Backup Protocols
* **If Conference Wi-Fi Fails:** Platform is pre-configured to run completely locally on `localhost:5173` via SQLite and cached synthetic fixtures with zero internet connectivity required.
* **If Browser Cache Glitches:** Open an Incognito window; demo accounts and seed data are initialized automatically in database storage.
