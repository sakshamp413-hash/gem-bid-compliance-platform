"""Model registry — import all models so metadata is complete."""
from app.models.user import User
from app.models.tender import Tender
from app.models.bidder import Bidder
from app.models.bid_submission import BidSubmission
from app.models.document import Document
from app.models.verification_check import VerificationCheck
from app.models.compliance_assessment import ComplianceAssessment
from app.models.officer_decision import OfficerDecision
from app.models.audit import AuditLog

all_models = [
    User,
    Tender,
    Bidder,
    BidSubmission,
    Document,
    VerificationCheck,
    ComplianceAssessment,
    OfficerDecision,
    AuditLog,
]

__all__ = [m.__name__ for m in all_models] + ["all_models"]