"""Error-correction adapters.

The core defines a small block-oriented interface (:mod:`.protocol`) and drives
it. Concrete codes register themselves on import so a serialized configuration
can be rebuilt by id, exactly like channels.
"""

from __future__ import annotations

from .none import NoErrorCorrection
from .protocol import (
    BlockResult,
    EccCost,
    ErrorCorrectingCodec,
    build_ecc,
    get_ecc_class,
    register_ecc,
)
from .repetition import RepetitionCode

__all__ = [
    "ErrorCorrectingCodec",
    "BlockResult",
    "EccCost",
    "register_ecc",
    "get_ecc_class",
    "build_ecc",
    "NoErrorCorrection",
    "RepetitionCode",
]
