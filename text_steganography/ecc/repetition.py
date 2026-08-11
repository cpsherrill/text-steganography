"""A repetition code.

Each message bit is written ``repeat`` times. Decoding takes a majority vote
over the copies that survived, ignoring erased ones. With ``repeat=3`` the code
corrects one flipped copy, or recovers a bit from a single surviving copy when
the other two are erased. An even split among the surviving copies is reported
as uncorrectable rather than guessed.

A repetition code is not efficient, but it is simple to reason about and it is
naturally erasure-aware, which matters here: text channels usually fail by
erasure (a variant normalized away) rather than by a clean bit flip. Denser
codes such as Reed-Solomon or BCH are future adapters that would wrap an
established library behind this same interface.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from .protocol import BlockResult, ErrorCorrectingCodec, register_ecc


@register_ecc
class RepetitionCode(ErrorCorrectingCodec):
    id = "ecc.repetition"
    version = "1"
    message_block_bits = 1

    def __init__(self, repeat: int = 3) -> None:
        if repeat < 1:
            raise ValueError("repeat must be at least 1")
        self.repeat = int(repeat)
        self.codeword_block_bits = self.repeat

    def encode_block(self, bits: Tuple[int, ...]) -> List[int]:
        return [bits[0]] * self.repeat

    def decode_block(self, observed: Sequence[Optional[int]]) -> BlockResult:
        known = [bit for bit in observed if bit is not None]
        if not known:
            return BlockResult(bits=None, corrected=0)
        ones = sum(known)
        zeros = len(known) - ones
        if ones == zeros:
            return BlockResult(bits=None, corrected=0)  # unbreakable tie
        decided = 1 if ones > zeros else 0
        corrected = sum(1 for bit in known if bit != decided)
        return BlockResult(bits=(decided,), corrected=corrected)

    def params(self) -> dict:
        return {"repeat": self.repeat}
