"""Compatibility import; implementation belongs to pai.workflows.counseling.service."""
import sys
from pai.workflows.counseling import service as _implementation
sys.modules[__name__] = _implementation
