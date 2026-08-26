"""
Tests: cross-submission collusion detection on the seeded demo tender.
"""
from app.db.session import SessionLocal
from app.models.bid_submission import BidSubmission
from app.models.bidder import Bidder
from app.services.collusion import _collect_attrs, detect_collusion


def _seed_demo():
    from app.db.session import init_db
    from app.seed import seed

    init_db()
    with SessionLocal() as db:
        if db.query(BidSubmission).count() == 0:
            seed(db)


def _tender_id(db) -> int:
    sub = db.query(BidSubmission).first()
    return sub.tender_id


def test_colluding_pair_is_clustered():
    _seed_demo()
    with SessionLocal() as db:
        result = detect_collusion(db, _tender_id(db))
        clusters = result["clusters"]
        assert len(clusters) == 1, clusters
        cluster = clusters[0]
        names = sorted(m["bidder_name"] for m in cluster["members"])
        assert "FrontRunner Pumps Pvt. Ltd." in names
        assert "QuickSpares Trading Co." in names
        # the shared attributes are bank account (exact) + signatory (fuzzy)
        attrs = set()
        for link in cluster["links"]:
            for a in link["attributes"]:
                attrs.add(a["attribute"])
        assert "bank_account" in attrs
        assert "signatory_name" in attrs


def test_independent_bidders_not_clustered():
    _seed_demo()
    with SessionLocal() as db:
        result = detect_collusion(db, _tender_id(db))
        for cluster in result["clusters"]:
            names = [m["bidder_name"] for m in cluster["members"]]
            # CleanCorp / Borderline / Kaveri / Southern are genuinely independent
            for independent in ("CleanCorp", "Borderline", "Kaveri", "Southern Pumps"):
                assert not any(independent in n for n in names), cluster


def test_attribute_collection_includes_bank_and_signatory():
    _seed_demo()
    with SessionLocal() as db:
        items = _collect_attrs(db, _tender_id(db))
        by_name = {i.bidder_name: i.attrs for i in items}
        fr = next(v for k, v in by_name.items() if "FrontRunner" in k)
        qs = next(v for k, v in by_name.items() if "QuickSpares" in k)
        assert fr["bank_account"] == "HDFC50200012345678"
        assert qs["bank_account"] == fr["bank_account"]
        assert "signatory_name" in fr and "signatory_name" in qs