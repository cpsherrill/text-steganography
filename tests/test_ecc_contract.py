"""F6 fixed-block contract tests; adapters here are dependency-free test doubles."""
from dataclasses import replace

import pytest
from hypothesis import given, settings, strategies as st

from text_steganography import (
    CapacityError, CodecConfig, ConfigError, DecodeStatus, RepetitionCode,
    TextSteganographyCodec, UnicodeSpaceChannel,
)
from text_steganography.core.bits import bytes_to_bits
from text_steganography.ecc.protocol import BlockResult, ErrorCorrectingCodec, register_ecc
from text_steganography.errors import FramingError
from text_steganography.models import ObservationState
from text_steganography.payload.framing import MAX_PAYLOAD_BYTES, frame, unframe
from text_steganography.payload.integrity import crc32


@register_ecc
class FixedBlock(ErrorCorrectingCodec):
    """Identity or per-bit repetition, grouped into blocks to test framing."""
    id = 'test.ecc.fixed_block'
    version = '1'

    def __init__(self, k=16, repeat=1):
        self.message_block_bits = k
        self.repeat = repeat
        self.codeword_block_bits = k * repeat

    def params(self):
        return {'k': self.message_block_bits, 'repeat': self.repeat}

    def encode_block(self, bits):
        return [bit for bit in bits for _ in range(self.repeat)]

    def decode_block(self, observed):
        bits, corrected = [], 0
        repetition = RepetitionCode(self.repeat)
        for start in range(0, len(observed), self.repeat):
            result = repetition.decode_block(observed[start:start + self.repeat])
            corrected += result.corrected
            if result.bits is None:
                return BlockResult(None, corrected)
            bits.extend(result.bits)
        return BlockResult(tuple(bits), corrected)


def codec(ecc, channel=None):
    return TextSteganographyCodec(CodecConfig(
        channels=[channel or UnicodeSpaceChannel()], error_correction=ecc,
    ))


def cover(capacity):
    return ' '.join(['w'] * (capacity + 1))


def render(bits):
    return 'w' + ''.join(('\u00a0' if bit else ' ') + 'w' for bit in bits)


def test_original_f6_sixteen_bit_header_reproduction():
    c = codec(FixedBlock(16))
    marked = c.encode(cover(200), b'x').text
    assert c.decode(marked).payload == b'x'


@pytest.mark.parametrize('k', [1, 7, 8, 16, 24, 64])
@pytest.mark.parametrize('repeat', [1, 3])
@pytest.mark.parametrize('payload_size', [0, 1, 2, 3, 6, 7, 8])
def test_frame_padding_capacity_and_round_trip(k, repeat, payload_size):
    ecc = FixedBlock(k, repeat)
    payload = bytes(range(payload_size))
    logical = 72 + len(payload) * 8
    expected_blocks = (logical + k - 1) // k
    encoded_size = expected_blocks * k * repeat
    assert ecc.codeword_len(logical) == encoded_size
    assert len(ecc.encode_bits(bytes_to_bits(frame(payload)))) == encoded_size
    c = codec(ecc)
    marked = c.encode(cover(encoded_size), payload)
    result = c.decode(marked.text)
    assert result.status is DecodeStatus.SUCCESS and result.payload == payload
    assert marked.unused_capacity_bits == 0
    report = c.analyze(cover(encoded_size))
    largest = bytes(report.usable_payload_bytes)
    assert c.decode(c.encode(cover(encoded_size), largest).text).payload == largest
    assert report.ecc_overhead_bits == ecc.codeword_len(72 + len(largest)*8) - (72 + len(largest)*8)
    with pytest.raises(CapacityError):
        c.encode(cover(encoded_size), largest + b'x')
    with pytest.raises(CapacityError):
        c.encode(cover(encoded_size - 1), payload)
    assert c.preflight(cover(encoded_size), [payload]).ok
    assert not c.preflight(cover(encoded_size - 1), [payload]).ok


@settings(max_examples=50, deadline=None)
@given(st.integers(min_value=1, max_value=80), st.binary(max_size=20))
def test_arbitrary_block_boundaries(k, payload):
    ecc = FixedBlock(k, 3)
    count = ecc.codeword_len((9 + len(payload))*8)
    c = codec(ecc)
    marked = c.encode(cover(count), payload).text
    assert c.decode(marked).payload == payload
    assert c.analyze(cover(count)).usable_payload_bytes >= len(payload)


@pytest.mark.parametrize('k', [1, 8, 16, 24])
def test_configuration_reload_and_candidate_predictions(k):
    c = codec(FixedBlock(k, 3))
    data = c.config.to_dict()
    restored = TextSteganographyCodec(CodecConfig.from_dict(data))
    assert restored.codec_id == c.codec_id
    recipients = [b'', b'\x00', b'\x01', b'\xff', b'long']
    text = cover(500)
    assert c.preflight(text, recipients).ok
    for payload in recipients:
        marked = c.encode(text, payload).text
        assert restored.decode(marked).payload == payload
        found = restored.identify(marked, recipients)
        assert found.unique and found.best().payload == payload


def test_header_trims_extra_bits_without_treating_payload_as_padding():
    ecc = FixedBlock(16)
    bits = bytes_to_bits(frame(b'\xff'))
    header = ecc.decode_prefix(ecc.encode_bits(bits), 40)
    assert header.status == 'ok' and header.bits == tuple(bits[:40])
    # The eight extra bits are payload ones, not the frame's trailing padding.
    assert ecc.decode_prefix(ecc.encode_bits(bits), 40, check_padding=True).status == 'invalid_padding'


def test_padding_is_after_crc_and_must_decode_to_zero():
    ecc = FixedBlock(16)
    bits = bytes_to_bits(frame(b''))
    encoded = ecc.encode_bits(bits)
    assert encoded == bits + [0] * 8
    encoded[-1] = 1  # CRC is intact, but the framing convention is violated.
    result = codec(ecc).decode(render(encoded))
    assert result.status is DecodeStatus.INVALID and result.payload is None


@pytest.mark.parametrize('cut', [1, 7, 16])
def test_incomplete_final_block_returns_insufficient_evidence(cut):
    ecc = FixedBlock(16, 3)
    encoded = ecc.encode_bits(bytes_to_bits(frame(b'test')))
    result = codec(ecc).decode(render(encoded[:-cut]))
    assert result.status is DecodeStatus.INSUFFICIENT_EVIDENCE and result.payload is None


def test_incomplete_header_block_returns_insufficient_evidence():
    result = codec(FixedBlock(16)).decode(render([0] * 47))
    assert result.status is DecodeStatus.INSUFFICIENT_EVIDENCE


class ErasableSpaces(UnicodeSpaceChannel):
    id = 'test.erasable_spaces'

    def __init__(self, erased=()):
        super().__init__()
        self.erased = set(erased)

    def observe(self, text, context=None):
        return [replace(obs, state=ObservationState.ERASED, symbol=None)
                if obs.ordinal in self.erased else obs
                for obs in super().observe(text, context)]


@pytest.mark.parametrize('start', [0, 48*3])
def test_block_ecc_recovers_errors_and_erasures_in_header_or_body(start):
    ecc = FixedBlock(16, 3)
    bits = ecc.encode_bits(bytes_to_bits(frame(b'test')))
    bits[start] ^= 1
    result = codec(ecc).decode(render(bits))
    assert result.payload == b'test' and result.corrected_errors == 1
    clean = render(ecc.encode_bits(bytes_to_bits(frame(b'test'))))
    result = codec(ecc, ErasableSpaces([start, start+1])).decode(clean)
    assert result.payload == b'test' and result.erasures == 2
    lost = codec(ecc, ErasableSpaces([start, start+1, start+2])).decode(clean)
    assert lost.status is DecodeStatus.PARTIAL and lost.payload is None


def test_uncorrectable_error_does_not_return_wrong_bytes():
    ecc = FixedBlock(16, 3)
    bits = ecc.encode_bits(bytes_to_bits(frame(b'x')))
    bits[120] ^= 1
    bits[121] ^= 1  # majority changes one payload bit, CRC must reject it
    result = codec(ecc).decode(render(bits))
    assert result.status is DecodeStatus.INVALID and result.payload is None


def test_unknown_frame_version_is_rejected_even_with_valid_crc():
    raw = bytearray(frame(b'x'))
    raw[2] = 2
    raw[-4:] = crc32(raw[:-4]).to_bytes(4, 'big')
    with pytest.raises(FramingError, match='version'):
        unframe(bytes(raw))
    with pytest.raises(FramingError, match='version'):
        frame(b'x', version=2)
    ecc = FixedBlock(16)
    result = codec(ecc).decode(render(ecc.encode_bits(bytes_to_bits(raw))))
    assert result.status is DecodeStatus.INVALID and result.frame_version == 2


def test_corrupted_length_does_not_read_past_available_blocks():
    raw = bytearray(frame(b'x'))
    raw[3:5] = b'\xff\xff'
    ecc = FixedBlock(16)
    result = codec(ecc).decode(render(ecc.encode_bits(bytes_to_bits(raw))))
    assert result.status is DecodeStatus.INSUFFICIENT_EVIDENCE and result.payload is None


@pytest.mark.parametrize('k,n', [(0, 1), (-1, 1), (1, 0), (8, 7), (True, 3), (1.5, 3), (1, 3.0)])
def test_invalid_adapter_sizes_are_rejected_at_configuration(k, n):
    ecc = FixedBlock()
    ecc.message_block_bits, ecc.codeword_block_bits = k, n
    with pytest.raises(ConfigError, match='block sizes'):
        codec(ecc)


@pytest.mark.parametrize('length', [-1, True, 2.5])
def test_size_helpers_reject_invalid_lengths(length):
    ecc = FixedBlock()
    for function in (ecc.codeword_len, ecc.message_len, ecc.padding_len):
        with pytest.raises(ConfigError, match='lengths'):
            function(length)


@pytest.mark.parametrize('output', [[0], [0]*17, [2]*16, [None]*16, [True]*16, '0'*16])
def test_malformed_encoded_blocks_are_adapter_errors(output):
    ecc = FixedBlock()
    ecc.encode_block = lambda bits: output
    with pytest.raises(ConfigError):
        codec(ecc).encode(cover(200), b'x')


@pytest.mark.parametrize('result', [
    None, (0,)*16, BlockResult((0,), 0), BlockResult((2,)*16, 0),
    BlockResult((None,)*16, 0), BlockResult((True,)*16, 0),
    BlockResult((0,)*16, -1), BlockResult((0,)*16, 17), BlockResult((0,)*16, True),
])
def test_malformed_decoded_blocks_are_adapter_errors(result):
    ecc = FixedBlock()
    ecc.decode_block = lambda bits: result
    with pytest.raises(ConfigError):
        codec(ecc).decode(cover(200))


def test_unexpected_adapter_exceptions_are_not_reported_as_transport_damage():
    def broken(bits):
        raise RuntimeError('adapter bug')
    ecc = FixedBlock()
    ecc.encode_block = broken
    with pytest.raises(ConfigError, match='failed to encode'):
        ecc.encode_bits([0]*16)
    ecc.decode_block = broken
    with pytest.raises(ConfigError, match='failed to decode'):
        ecc.decode_prefix([0]*16, 16)


@pytest.mark.parametrize('bits', [[2], [None], [True], ['0']])
def test_invalid_message_bits_are_rejected(bits):
    with pytest.raises(ConfigError, match='binary'):
        FixedBlock().encode_bits(bits)


@pytest.mark.parametrize('bits', [[0]*15, [2]*16, [True]*16])
def test_invalid_observation_blocks_are_rejected(bits):
    with pytest.raises(ConfigError):
        FixedBlock().decode_block_checked(bits)


def test_zero_length_prefix_and_message():
    ecc = FixedBlock()
    assert ecc.encode_bits([]) == []
    assert ecc.codeword_len(0) == 0
    assert ecc.decode_prefix([], 0, check_padding=True).bits == ()


@pytest.mark.parametrize('layout', [None, {}, {'message_bits': 16, 'codeword_bits': 16, 'padding': 'other'}])
def test_incompatible_serialized_block_layout_is_rejected(layout):
    data = codec(FixedBlock()).config.to_dict()
    if layout is None:
        del data['error_correction']['block_layout']
    else:
        data['error_correction']['block_layout'] = layout
    with pytest.raises(ConfigError, match='block_layout'):
        CodecConfig.from_dict(data)


def test_capacity_honors_frame_payload_limit_without_huge_site_fixture(monkeypatch):
    # Isolate framing capacity arithmetic from allocating half a million sites.
    from types import SimpleNamespace
    import text_steganography.codec as module
    plan = SimpleNamespace(planned_sites=[SimpleNamespace(
        channel_index=0, width=(MAX_PAYLOAD_BYTES + 100)*8, site=SimpleNamespace(radix=2),
    )], warnings=[])
    monkeypatch.setattr(module, 'build_plan', lambda config, text: plan)
    report = codec(FixedBlock()).analyze('')
    assert report.usable_payload_bytes == MAX_PAYLOAD_BYTES
    with pytest.raises(FramingError, match='frame limit'):
        frame(bytes(MAX_PAYLOAD_BYTES + 1))


def test_empty_payload_cli_json_is_empty_hex_not_missing(tmp_path, capsys):
    import json
    from text_steganography.cli.main import main
    source, marked = tmp_path/'cover.txt', tmp_path/'marked.txt'
    source.write_text(cover(100), encoding='utf-8')
    assert main(['encode', '-i', str(source), '-o', str(marked), '--hex', '']) == 0
    capsys.readouterr()
    assert main(['decode', '-i', str(marked), '--json']) == 0
    assert json.loads(capsys.readouterr().out)['payload_hex'] == ''
