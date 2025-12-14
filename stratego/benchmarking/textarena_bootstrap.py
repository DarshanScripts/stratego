"""
Bootstrap to prevent duplicate TextArena environment registration.

This file MUST be imported before ANY textarena env imports.
"""

import textarena.envs.registration as _reg

# Keep original functions
_original_register = _reg.register
_original_register_with_versions = _reg.register_with_versions

def safe_register(*, id: str, **kwargs):
    """
    Prevent duplicate register() calls.
    """
    if id in _reg.ENV_REGISTRY:
        return
    return _original_register(id=id, **kwargs)

def safe_register_with_versions(*, id: str, **kwargs):
    """
    Prevent duplicate register_with_versions() calls.
    """
    if id in _reg.ENV_REGISTRY:
        return
    return _original_register_with_versions(id=id, **kwargs)

# 🔒 Monkey-patch both
_reg.register = safe_register
_reg.register_with_versions = safe_register_with_versions
