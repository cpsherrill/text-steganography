"""The identity (no error correction) codec.

Every message bit is its own codeword bit. An erased observation stays erased.
This is the default, and it makes the ECC layer a no-op: a configuration that
uses it produces byte-identical output to a pipeline with no ECC at all, which
is what keeps earlier configurations and golden vectors valid.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .protocol import BlockResult, ErrorCorrectingCodec, register_ecc


@register_ecc
class NoErrorCorrection(ErrorCorrectingCodec):
    id = "ecc.none"
    version = "1"
    message_block_bits = 1
    codeword_block_bits = 1

    def encode_block(self, bits: Tuple[int, ...]) -> List[int]:
        return [bits[0]]

    def decode_block(self, observed: Sequence[Optional[int]]) -> BlockResult:
        value = observed[0]
        if value is None:
            return BlockResult(bits=None, corrected=0)
        return BlockResult(bits=(value,), corrected=0)
