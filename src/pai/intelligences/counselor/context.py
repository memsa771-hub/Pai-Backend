"""Compatibility import; implementation belongs to pai.workflows.counseling.context."""
import sys
from pai.workflows.counseling import context as _implementation
sys.modules[__name__] = _implementation
