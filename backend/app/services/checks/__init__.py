"""All compliance check modules, exposed as a flat API."""
from app.services.checks.base import CheckOutput, Evidence, add_evidence, check_registry  # noqa: F401
from app.services.checks.udyam import check_udyam
from app.services.checks.gst import check_gst
from app.services.checks.pan import check_pan
from app.services.checks.mca import check_mca
from app.services.checks.local_content import check_local_content
from app.services.checks.epfo import check_epfo
from app.services.checks.esic import check_esic
from app.services.checks.startup import check_startup
from app.services.checks.nsic import check_nsic
from app.services.checks.oem import check_oem
from app.services.checks.digilocker import check_digilocker
from app.services.checks.blacklist import check_blacklist

__all__ = [
    "CheckOutput", "Evidence", "add_evidence", "check_registry",
    "check_udyam", "check_gst", "check_pan", "check_mca", "check_local_content",
    "check_epfo", "check_esic", "check_startup", "check_nsic", "check_oem",
    "check_digilocker", "check_blacklist",
]