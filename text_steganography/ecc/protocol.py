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
class PrefixResult:
    """A decoded logical prefix, with padding removed only after validation.

    Status is ok, insufficient, uncorrectable, or invalid_padding. Adapter
    contract violations raise ConfigError rather than reporting damaged input.
    """

    bits: Optional[Tuple[int, ...]]
    corrected: int
    status: str


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

    def validate(self) -> None:
        """Validate a fixed-block, non-compressing adapter definition."""
        k, n = self.message_block_bits, self.codeword_block_bits
        if type(k) is not int or type(n) is not int or k < 1 or n < k:
            raise ConfigError("ECC block sizes must be positive integers with codeword bits >= message bits")
        if not isinstance(self.id, str) or not self.id or not isinstance(self.version, str) or not self.version:
            raise ConfigError("ECC adapters require nonempty string ids and versions")
        if self.id == "ecc.none" and (k, n) != (1, 1):
            raise ConfigError("ecc.none is reserved for the one-bit identity codec")

    def block_layout(self) -> Dict[str, object]:
        """The wire convention shared by fixed-block adapters."""
        self.validate()
        return {"message_bits": self.message_block_bits,
                "codeword_bits": self.codeword_block_bits, "padding": "zero_pad_v1"}

    @staticmethod
    def _length(value: int) -> None:
        if type(value) is not int or value < 0:
            raise ConfigError("ECC bit lengths must be nonnegative integers")

    @staticmethod
    def _bits(values, *, size: Optional[int] = None, erasures: bool = False) -> None:
        if not isinstance(values, (list, tuple)):
            raise ConfigError("ECC bits must be a list or tuple")
        if size is not None and len(values) != size:
            raise ConfigError(f"ECC block has {len(values)} bits; expected {size}")
        if any(not (erasures and bit is None) and
               (type(bit) is not int or bit not in (0, 1)) for bit in values):
            raise ConfigError("ECC values must be binary integers (or None for erasures)")

    def padding_len(self, message_len: int) -> int:
        self.validate()
        self._length(message_len)
        return (-message_len) % self.message_block_bits

    def encode_bits(self, message_bits: Sequence[int]) -> List[int]:
        """Encode a logical message, appending zeros to the last whole block.

        Callers retain the logical length in framing. Empty input has no blocks.
        Padding belongs to this shared layer, not individual adapters.
        """
        self.validate()
        bits = list(message_bits)
        self._bits(bits)
        bits.extend([0] * self.padding_len(len(bits)))
        k = self.message_block_bits
        out: List[int] = []
        for i in range(0, len(bits), k):
            try:
                encoded = self.encode_block(tuple(bits[i:i + k]))
            except Exception as error:
                raise ConfigError(f"ECC adapter {self.id!r} failed to encode a block") from error
            self._bits(encoded, size=self.codeword_block_bits)
            out.extend(encoded)
        return out

    def decode_block_checked(self, observed: Sequence[Optional[int]]) -> BlockResult:
        """Call an adapter while enforcing input/output shape and bit values."""
        self.validate()
        block = tuple(observed)
        self._bits(block, size=self.codeword_block_bits, erasures=True)
        try:
            result = self.decode_block(block)
        except Exception as error:
            raise ConfigError(f"ECC adapter {self.id!r} failed to decode a block") from error
        if not isinstance(result, BlockResult):
            raise ConfigError("ECC decode must return a BlockResult")
        known = sum(bit is not None for bit in block)
        if type(result.corrected) is not int or not 0 <= result.corrected <= known:
            raise ConfigError("ECC corrected count must count known positions within this block")
        if result.bits is not None:
            self._bits(result.bits, size=self.message_block_bits)
        return result

    def decode_prefix(
        self, observed: Sequence[Optional[int]], message_len: int, *, check_padding: bool = False
    ) -> PrefixResult:
        """Read ceiling(message_len/k) blocks and return exactly message_len bits.

        Only a complete frame uses check_padding=True. A header's last block
        may also contain payload bits, which must not be mistaken for padding.
        """
        needed = self.codeword_len(message_len)
        if len(observed) < needed:
            return PrefixResult(None, 0, "insufficient")
        bits: List[int] = []
        corrected = 0
        for start in range(0, needed, self.codeword_block_bits):
            result = self.decode_block_checked(observed[start:start + self.codeword_block_bits])
            corrected += result.corrected
            if result.bits is None:
                return PrefixResult(None, corrected, "uncorrectable")
            bits.extend(result.bits)
        if check_padding and any(bits[message_len:]):
            return PrefixResult(None, corrected, "invalid_padding")
        return PrefixResult(tuple(bits[:message_len]), corrected, "ok")

    def codeword_len(self, message_len: int) -> int:
        """Encoded size including final-block padding and ECC redundancy."""
        self.validate()
        self._length(message_len)
        return ((message_len + self.padding_len(message_len)) // self.message_block_bits
                * self.codeword_block_bits)

    def message_len(self, codeword_len: int) -> int:
        """Whole message bits recoverable; incomplete encoded blocks add none."""
        self.validate()
        self._length(codeword_len)
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
    try:
        codec = cls.from_params(params)
    except (TypeError, ValueError) as error:
        raise ConfigError(f"invalid parameters for ECC adapter {ecc_id!r}") from error
    codec.validate()
    return codec
