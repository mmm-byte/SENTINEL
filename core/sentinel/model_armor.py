"""Re-export the existing Model Armor implementation under the core namespace.

The original module lives in `agent/model_armor.py` and is unchanged. This
file just provides a stable import path (`core.sentinel.model_armor`) that
the publishing script can copy verbatim into per-track repos.
"""
from agent.model_armor import (  # noqa: F401
    ArmorPolicy,
    ArmorViolation,
    ModelArmor,
)

__all__ = ["ArmorPolicy", "ArmorViolation", "ModelArmor"]
