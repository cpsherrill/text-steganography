"""The error-correction adapter interface.

The steganography core does not hard-code any coding algorithm. It defines a
small, block-oriented interface and drives it; concrete codes plug in behind
it. A code declares a block size in message bits (``k``) and codeword bits
(``n``), and implements two operations on one block: encode ``k`` bits into
``n``, and decode ``n`` observed bits (some possibly erased) back into ``k``.

Working in whole blocks is what lets the decoder read the frame header before
it knows the frame length: the header is a fixed number of leading message
bits, so it occupies a fixed number of leading codeword blocks, which can be
decoded first. Interleaving, which would spread a block across the text, is a
deliberately separate feature so this incremental decode stays possible.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple, Type

from ..errors import ConfigError


@dataclass(frozen=True)
class BlockResult:
    """The decode of one codeword block.

    ``bits`` holds the recovered ``k`` message bits, or is ``None`` when the
    block is uncorrectable (too many erasures, or an unbreakable tie).
    ``corrected`` counts observed positions that disagreed with the decision.
    """

    bits: Optional[Tuple[int, ...]]
    corrected: int


@dataclass(frozen=True)
class EccCost:
    """The size cost of protecting a message of a given bit length."""

    message_bits: int
    codeword_bits: int

    @property
    def redundancy_bits(self) -> int:
        return self.codeword_bits - self.message_bits


class ErrorCorrectingCodec(ABC):
    """A block error-correcting code behind a uniform interface."""

    id: str = ""
    version: str = ""
    message_block_bits: int = 1
    codeword_block_bits: int = 1

    @abstractmethod
    def encode_block(self, bits: Tuple[int, ...]) -> List[int]:
        """Encode ``message_block_bits`` bits into ``codeword_block_bits``."""

    @abstractmethod
    def decode_block(self, observed: Sequence[Optional[int]]) -> BlockResult:
        """Decode one codeword block; ``None`` entries are erasures."""

    def encode_bits(self, message_bits: Sequence[int]) -> List[int]:
        k = self.message_block_bits
        if len(message_bits) % k != 0:
            raise ValueError(f"message bit count {len(message_bits)} is not a multiple of {k}")
        out: List[int] = []
        for i in range(0, len(message_bits), k):
            out.extend(self.encode_block(tuple(message_bits[i : i + k])))
        return out

    def codeword_len(self, message_len: int) -> int:
        """Codeword bit length for a message of ``message_len`` bits."""
        k = self.message_block_bits
        blocks = (message_len + k - 1) // k
        return blocks * self.codeword_block_bits

    def message_len(self, codeword_len: int) -> int:
        """Whole message bits recoverable from ``codeword_len`` codeword bits."""
        return (codeword_len // self.codeword_block_bits) * self.message_block_bits

    def capacity_cost(self, message_bits: int) -> EccCost:
        return EccCost(message_bits=message_bits, codeword_bits=self.codeword_len(message_bits))

    def params(self) -> Dict[str, object]:
        return {}

    @classmethod
    def from_params(cls, params: Dict[str, object]) -> "ErrorCorrectingCodec":
        return cls(**params)  # type: ignore[arg-type]


_REGISTRY: Dict[str, Type[ErrorCorrectingCodec]] = {}


def register_ecc(cls: Type[ErrorCorrectingCodec]) -> Type[ErrorCorrectingCodec]:
    if not cls.id:
        raise ConfigError(f"ecc {cls.__name__} must define a non-empty id")
    existing = _REGISTRY.get(cls.id)
    if existing is not None and existing is not cls:
        raise ConfigError(f"ecc id {cls.id!r} is already registered to {existing.__name__}")
    _REGISTRY[cls.id] = cls
    return cls


def get_ecc_class(ecc_id: str) -> Type[ErrorCorrectingCodec]:
    try:
        return _REGISTRY[ecc_id]
    except KeyError:
        raise ConfigError(f"unknown ecc id {ecc_id!r}") from None


def build_ecc(ecc_id: str, version: str, params: Dict[str, object]) -> ErrorCorrectingCodec:
    cls = get_ecc_class(ecc_id)
    if version and cls.version and version != cls.version:
        raise ConfigError(
            f"ecc {ecc_id!r} version mismatch: config wants {version!r}, installed is {cls.version!r}"
        )
    return cls.from_params(params)
