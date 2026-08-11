from __future__ import annotations

import pytest

from text_steganography.ecc import NoErrorCorrection, RepetitionCode
from text_steganography.ecc.protocol import build_ecc


def test_none_is_identity():
    ecc = NoErrorCorrection()
    bits = [1, 0, 1, 1, 0, 0, 1, 0]
    assert ecc.encode_bits(bits) == bits
    assert ecc.codeword_len(8) == 8
    assert ecc.message_len(8) == 8


def test_none_erasure_is_uncorrectable():
    ecc = NoErrorCorrection()
    assert ecc.decode_block([None]).bits is None
    assert ecc.decode_block([1]).bits == (1,)


def test_repetition_encode_lengths():
    ecc = RepetitionCode(repeat=3)
    assert ecc.encode_bits([1, 0]) == [1, 1, 1, 0, 0, 0]
    assert ecc.codeword_len(8) == 24
    assert ecc.message_len(24) == 8
    assert ecc.message_len(25) == 8  # partial trailing block is not usable


def test_repetition_corrects_one_flipped_copy():
    ecc = RepetitionCode(repeat=3)
    result = ecc.decode_block([1, 0, 1])  # majority is 1, one copy flipped
    assert result.bits == (1,)
    assert result.corrected == 1


def test_repetition_recovers_from_erasures():
    ecc = RepetitionCode(repeat=3)
    result = ecc.decode_block([None, None, 0])  # one surviving copy
    assert result.bits == (0,)


def test_repetition_reports_unbreakable_tie():
    ecc = RepetitionCode(repeat=2)
    assert ecc.decode_block([0, 1]).bits is None  # 1-1 split, no majority


def test_repetition_all_erased_is_uncorrectable():
    ecc = RepetitionCode(repeat=3)
    assert ecc.decode_block([None, None, None]).bits is None


def test_repetition_round_trip_bits():
    ecc = RepetitionCode(repeat=5)
    message = [1, 0, 0, 1, 1, 1, 0, 1]
    codeword = ecc.encode_bits(message)
    # decode block by block
    recovered = []
    for i in range(0, len(codeword), 5):
        recovered.extend(ecc.decode_block(codeword[i : i + 5]).bits)
    assert recovered == message


def test_repetition_rejects_bad_repeat():
    with pytest.raises(ValueError):
        RepetitionCode(repeat=0)


def test_registry_round_trip():
    ecc = build_ecc("ecc.repetition", "1", {"repeat": 3})
    assert isinstance(ecc, RepetitionCode)
    assert ecc.params() == {"repeat": 3}
