from __future__ import annotations

import pytest

from text_steganography import (
    CapacityError,
    CodecConfig,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)


def make_codec() -> TextSteganographyCodec:
    return TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()]))


def cover_with_words(n: int) -> str:
    return " ".join(["word"] * n)


def test_capacity_matches_site_count():
    codec = make_codec()
    report = codec.analyze(cover_with_words(100))  # 99 inter-word spaces
    assert report.total_sites == 99
    assert report.realizable_packed_bits == 99
    assert report.per_channel[0].channel_id == "whitespace.unicode_space"
    assert report.per_channel[0].sites == 99


def test_overhead_is_reported_separately():
    report = make_codec().analyze(cover_with_words(100))
    assert report.framing_overhead_bits == 40
    assert report.integrity_overhead_bits == 32
    assert report.ecc_overhead_bits == 0


def test_usable_capacity_subtracts_overhead():
    # 99 bits realizable, minus 72 bits overhead, is 27 bits, floored to 3 bytes
    report = make_codec().analyze(cover_with_words(100))
    assert report.usable_payload_bytes == 3
    assert report.usable_payload_bits == 24
    assert report.max_distinct_payloads == 2**24


def test_low_capacity_text_reports_nothing_usable():
    report = make_codec().analyze(cover_with_words(20))  # 19 bits, below the frame floor
    assert report.usable_payload_bytes == 0
    assert report.max_distinct_payloads == 0


def test_analyze_and_encode_agree_on_the_limit():
    codec = make_codec()
    cover = cover_with_words(100)
    usable = codec.analyze(cover).usable_payload_bytes
    # a payload at the reported limit fits
    codec.encode(cover, b"\x00" * usable)
    # one byte over the reported limit does not
    with pytest.raises(CapacityError):
        codec.encode(cover, b"\x00" * (usable + 1))


@pytest.mark.parametrize('sites,exponent,numeric,display', [
    (71, None, 0, '0'),
    (72, 0, 1, '1'),
    (80, 8, 256, '256'),
    (120, 48, 2**48, str(2**48)),
    (128, 56, None, '2^56'),
    (16000, 15928, None, '2^15928'),
])
def test_capacity_report_stores_exponent_and_serializes_safely(sites, exponent, numeric, display):
    from dataclasses import asdict
    import json
    report = make_codec().analyze(cover_with_words(sites + 1))
    assert report.max_distinct_payloads_log2 == exponent
    assert report.max_distinct_payloads == (0 if exponent is None else 2**exponent)
    assert report.max_distinct_payloads_display == display
    raw = asdict(report)
    assert raw['max_distinct_payloads_log2'] == exponent
    assert 'max_distinct_payloads' not in raw
    serialized = json.loads(json.dumps(report.to_dict()))
    assert serialized['max_distinct_payloads'] == numeric
    assert serialized['max_distinct_payloads_log2'] == exponent
    assert serialized['per_channel'][0]['sites'] == sites
    assert len(str(report)) < 2000
    assert len(repr(report)) < 2000


@pytest.mark.parametrize('limit', ['640', '4300'])
def test_report_logging_and_serialization_under_integer_limit(limit):
    import os
    import subprocess
    import sys
    # Isolate interpreter settings. Exercise the actual API under both the
    # minimum supported limit and Python's default without relaxing either.
    code = '''
import io
import json
import logging
import sys
from dataclasses import asdict
from text_steganography import CodecConfig, TextSteganographyCodec, UnicodeSpaceChannel
c = TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()]))
r = c.analyze(' '.join(['word'] * 16001))
assert r.max_distinct_payloads_log2 == 15928
assert r.max_distinct_payloads.bit_length() == 15929
assert len(str(r)) < 2000 and len(repr(r)) < 2000
assert json.loads(json.dumps(asdict(r)))['max_distinct_payloads_log2'] == 15928
assert json.loads(json.dumps(r.to_dict()))['max_distinct_payloads'] is None
stream = io.StringIO()
logger = logging.getLogger('report-regression')
logger.addHandler(logging.StreamHandler(stream))
logger.warning('Capacity: %s', r)
assert 'max_distinct_payloads_log2=15928' in stream.getvalue()
# An explicit request to format the enormous exact integer still follows
# Python's safety limit; supported report serialization never does this.
if hasattr(sys, 'get_int_max_str_digits'):
    assert sys.get_int_max_str_digits() == int(sys.argv[1])
    try:
        json.dumps(r.max_distinct_payloads)
    except ValueError:
        pass
    else:
        raise AssertionError('explicit integer formatting should hit the limit')
'''
    result = subprocess.run([sys.executable, '-c', code, limit], text=True,
                            capture_output=True, timeout=20,
                            env={**os.environ, 'PYTHONINTMAXSTRDIGITS': limit})
    assert result.returncode == 0, result.stderr
    assert not result.stderr
