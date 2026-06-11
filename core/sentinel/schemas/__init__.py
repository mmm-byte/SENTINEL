"""Re-export the Handshake schema under the core namespace."""
from agent.schemas.handshake import (  # noqa: F401
    Handshake,
    Stage,
)

__all__ = ["Handshake", "Stage"]
