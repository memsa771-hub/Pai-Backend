"""Compatibility import for counseling workflow."""
import sys
from pai.workflows.counseling import opening as _implementation
sys.modules[__name__] = _implementation
