"""
Comprehensive test suite for P0 Engineering Features:
- F01: Tender Requirement Compiler (regex/NLP ATC text extraction)
- F02: Corrigendum Impact Analyzer (tender vs corrigendum diff & affected bidders)
- F03: Vendor Compliance Digital Twin (readiness score & gap items cache)
- F04: Bid Readiness Remediation Engine (prioritised gap-closing action plan)
- F05: Procurement Integrity Graph Visualizer (D3-compatible node-link JSON)
- F06: Decision Replay Engine (step-by-step verification playback for auditors)
- F07: Redis Asynchronous Worker Queue (job enqueuing and polling status)
"""
from __future__ import annotations

from app.models.bid_submission import BidSubmission
from app.models.bidder import Bidder
from app.models.tender import Tender
from tests.conftest import auth_headers, login


SAMPLE_ATC_TEXT = """
1. ELIGIBILITY CRITERIA:
The Bidder must have an average annual turnover of at least Rs. 15.5 Crore in the last 3 financial years.
2. MAKE IN INDIA PREFERENCE:
Purchase preference will be given to Class-I local content suppliers with minimum 50% local content.
3. MSME BENEFITS:
Micro and Small Enterprises holding valid Udyam Registration Certificate are exempted from prior turnover criteria.
4. EARNEST MONEY DEPOSIT:
Bidder must submit an Earnest Money Deposit (EMD) of Rs. 2,50,000 via Bank Guarantee.
5. MANDATORY REGISTRATIONS:
Bidder must possess valid GSTIN registration and PAN card.
6. INTEGRITY PACT:
The firm must not be blacklisted or debarred by any Central/State Government Ministry or GeM.
"""

SAMPLE_CORRIGENDUM_TEXT = """
CORRIGENDUM NO. 1
AMENDMENT TO TENDER ELIGIBILITY CONDITIONS:
1. Minimum annual turnover requirement is relaxed from 15.5 Crore to 8.0 Crore.
2. Local content percentage requirement modified: minimum 40% local content required.
3. Last date of bid submission is extended to 2026-10-15.
"""


def test_f01_tender_compiler():
    """F01: Test Tender Requirement Compiler extracts structured rules from ATC text."""
    from app.ai.tender_compiler import compile_tender_requirements

    compiled = compile_tender_requirements(SAMPLE_ATC_TEXT)
    assert len(compiled) >= 4

    categories = {r.category for r in compiled}
    assert "turnover" in categories
    assert "local_content" in categories
    assert "msme" in categories

    # Verify severity ordering: critical items come first
    severities = [r.severity for r in compiled]
    assert severities[0] in ("critical", "high")

    # Check threshold parsing
    turnover_req = next(r for r in compiled if r.category == "turnover")
    assert turnover_req.threshold_value is not None
    assert turnover_req.doc_required == "financial_statement"

    local_req = next(r for r in compiled if r.category == "local_content")
    assert local_req.threshold_value == "50"
    assert local_req.threshold_unit == "%"


def test_f02_corrigendum_analyzer(client, db):
    """F02: Test Corrigendum Impact Analyzer diffs requirements and flags affected bidders."""
    token = login(client)["access_token"]
    headers = auth_headers(token)

    tender = db.query(Tender).first()
    assert tender is not None

    # Post corrigendum via API
    resp = client.post(
        f"/tenders/{tender.id}/corrigenda",
        data={
            "corrigendum_number": 1,
            "title": "Corrigendum 1 - Turnover Relaxation",
            "text_content": SAMPLE_CORRIGENDUM_TEXT,
        },
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["tender_id"] == tender.id
    assert data["corrigendum_number"] == 1
    assert data["total_changes"] >= 1
    assert isinstance(data["affected_bidder_ids"], list)

    # List corrigenda endpoint
    list_resp = client.get(f"/tenders/{tender.id}/corrigenda", headers=headers)
    assert list_resp.status_code == 200
    corr_list = list_resp.json()
    assert len(corr_list) >= 1
    assert corr_list[0]["corrigendum_number"] == 1


def test_f03_vendor_digital_twin_readiness(client, db):
    """F03: Test Vendor Digital Twin computes readiness score and gap items."""
    token = login(client)["access_token"]
    headers = auth_headers(token)

    tender = db.query(Tender).first()
    bidder = db.query(Bidder).first()
    assert tender is not None and bidder is not None

    resp = client.get(
        f"/vendors/{bidder.id}/readiness?tender_id={tender.id}",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "readiness_score" in data
    assert 0.0 <= data["readiness_score"] <= 100.0
    assert "gap_items" in data
    assert len(data["gap_items"]) > 0

    # Ensure required items are evaluated (pan, gst, etc.)
    req_ids = {g["requirement_id"] for g in data["gap_items"]}
    assert "pan" in req_ids
    assert "gst" in req_ids


def test_f04_remediation_engine(client, db):
    """F04: Test Bid Readiness Remediation Engine creates prioritised gap-closing action plan."""
    token = login(client)["access_token"]
    headers = auth_headers(token)

    sub = db.query(BidSubmission).filter(BidSubmission.status == "assessed").first()
    if sub is None:
        sub = db.query(BidSubmission).first()
    assert sub is not None

    resp = client.get(
        f"/vendors/{sub.bidder_id}/remediation?submission_id={sub.id}",
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["submission_id"] == sub.id
    assert data["bidder_id"] == sub.bidder_id
    assert "tasks" in data
    assert "source_badge" in data

    # Check tasks format if any checks were flagged/failed
    for task in data["tasks"]:
        assert task["severity"] in ("CRITICAL", "HIGH", "MEDIUM", "LOW")
        assert len(task["action"]) > 0
        assert task["resolved"] is False


def test_f05_collusion_graph(client, db):
    """F05: Test Procurement Integrity Graph endpoint returns D3 node-link format JSON."""
    token = login(client)["access_token"]
    headers = auth_headers(token)

    tender = db.query(Tender).first()
    assert tender is not None

    resp = client.get(f"/tenders/{tender.id}/collusion/graph", headers=headers)
    assert resp.status_code == 200, resp.text
    graph = resp.json()

    assert "nodes" in graph
    assert "links" in graph
    assert "clusters" in graph
    assert "metadata" in graph

    assert graph["metadata"]["tender_id"] == tender.id
    assert graph["metadata"]["node_count"] == len(graph["nodes"])
    assert graph["metadata"]["risk_level"] in ("low", "high", "critical")

    for node in graph["nodes"]:
        assert "id" in node
        assert "label" in node
        assert "group" in node
        assert "suspicious" in node


def test_f06_decision_replay(client, db):
    """F06: Test Decision Replay Engine reconstructs chronological audit playback."""
    token = login(client)["access_token"]
    headers = auth_headers(token)

    sub = db.query(BidSubmission).filter(BidSubmission.status == "assessed").first()
    if sub is None:
        sub = db.query(BidSubmission).first()
    assert sub is not None

    resp = client.get(f"/submissions/{sub.id}/replay", headers=headers)
    assert resp.status_code == 200, resp.text
    replay = resp.json()

    assert replay["submission_id"] == sub.id
    assert "steps" in replay
    assert len(replay["steps"]) >= 1

    # Verify chronological sequence
    step_seqs = [s["seq"] for s in replay["steps"]]
    assert step_seqs == list(range(1, len(replay["steps"]) + 1))

    # Check step structure
    for s in replay["steps"]:
        assert "title" in s
        assert "event_type" in s
        assert "result" in s

    assert "summary" in replay
    assert "total_steps" in replay["summary"]


def test_f07_async_jobs(client, db):
    """F07: Test Async Job enqueuing and polling status endpoint."""
    token = login(client)["access_token"]
    headers = auth_headers(token)

    sub = db.query(BidSubmission).first()
    assert sub is not None

    # Enqueue an assessment job
    resp = client.post(f"/jobs/assess?submission_id={sub.id}", headers=headers)
    assert resp.status_code == 200, resp.text
    job_info = resp.json()

    assert "job_id" in job_info
    job_id = job_info["job_id"]

    # Poll status
    status_resp = client.get(f"/jobs/{job_id}", headers=headers)
    assert status_resp.status_code == 200, status_resp.text
    status_data = status_resp.json()

    assert status_data["job_id"] == job_id
    assert status_data["status"] in ("queued", "running", "done", "failed")
    assert 0.0 <= status_data["progress_pct"] <= 100.0
