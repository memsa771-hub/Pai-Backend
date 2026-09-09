"""Compatibility import for counseling workflow."""
import sys
from pai.workflows.counseling import followup as _implementation
sys.modules[__name__] = _implementation
