"""Measured local paths and explicit examples of recoverable/unrecoverable damage."""
import json
from pathlib import Path
import subprocess
import sys
import unicodedata

import pytest
from hypothesis import given, settings, strategies as st

from text_steganography import (
    CodecConfig, ConfigError, DecodeStatus, MarkdownCarrier, RepetitionCode,
    TextSteganographyCodec, UnicodeSpaceChannel, build_probe,
)

ROOT = Path(__file__).resolve().parents[1]


def codec(repeat=1):
    return TextSteganographyCodec(CodecConfig(
        channels=[UnicodeSpaceChannel()], error_correction=RepetitionCode(repeat),
    ))


def test_local_transport_recorder_is_reproducible(tmp_path):
    output = tmp_path / 'evidence'
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'validate_local_transports.py'), str(output)],
                   cwd=ROOT, capture_output=True, text=True, check=True, timeout=30)
    result = json.loads((output / 'results.json').read_text())
    assert len(result['results']) == 3
    for row in result['results']:
        assert row['decode_status'] == 'success' and row['payload_matches']
        assert row['unique_correct_candidate'] and row['probe_survival'] == 1
        for sample in row['samples'].values():
            assert sample['byte_identical'] and sample['sent_sha256'] == sample['returned_sha256']
    # Never overwrite saved empirical evidence with a later experiment.
    retry = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'validate_local_transports.py'), str(output)],
                           cwd=ROOT, capture_output=True, timeout=30)
    assert retry.returncode != 0


@pytest.mark.parametrize('line_ending', ['\n', '\r\n'])
def test_line_endings_preserve_payload_and_identification(line_ending):
    c = codec()
    cover = '\n'.join(' '.join(f'word{i}_{j}' for j in range(30)) for i in range(20))
    marked = c.encode(cover, b'recipient').text.replace('\n', line_ending)
    assert c.decode(marked).payload == b'recipient'
    result = c.identify(marked, [b'recipient', b'other'])
    assert result.unique and result.best().payload == b'recipient'


def test_local_normalization_loses_payload_despite_unchanged_site_count():
    c = codec(3)
    cover = 'word ' * 1000
    marked = c.encode(cover, b'recipient').text
    returned = unicodedata.normalize('NFKC', marked)
    assert c.analyze(returned).total_sites == c.analyze(marked).total_sites
    assert c.decode(returned).status is DecodeStatus.INVALID
    assert not c.identify(returned, [b'recipient', b'other']).unique
    probe = build_probe(c.config, cover)
    assert probe.evaluate(unicodedata.normalize('NFKC', probe.stego)).overall_survival == 0


@pytest.mark.parametrize('copies,recovers', [(1, True), (2, False)])
def test_repetition_boundary_on_a_damaged_payload_bit(copies, recovers):
    c = codec(3)
    marked = c.encode('word ' * 600, b'recipient').text
    sites = UnicodeSpaceChannel().discover_sites(marked)
    chars = list(marked)
    # First payload bit begins after the 40-bit header, repeated three times.
    for index in range(120, 120 + copies):
        position = sites[index].start
        chars[position] = ' ' if chars[position] == '\u00a0' else '\u00a0'
    result = c.decode(''.join(chars))
    assert (result.payload == b'recipient') is recovers
    if not recovers:
        assert result.status is DecodeStatus.INVALID


@settings(max_examples=50, deadline=None)
@given(st.text(max_size=300))
def test_arbitrary_unmarked_unicode_returns_a_structured_decode_result(text):
    result = codec().decode(text)
    assert isinstance(result.status, DecodeStatus)
    if result.status is not DecodeStatus.SUCCESS:
        assert result.payload is None


def test_markdown_v2_config_is_not_silently_reinterpreted():
    config = CodecConfig(channels=[UnicodeSpaceChannel()], carrier=MarkdownCarrier()).to_dict()
    assert config['carrier']['version'] == '3'
    config['carrier']['version'] = '2'
    with pytest.raises(ConfigError, match='version mismatch'):
        CodecConfig.from_dict(config)


def test_multiline_reference_definition_is_fully_protected():
    protected = '[ref]:\n  https://example.test/path\n  "multiline title words"\n'
    c = TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()], carrier=MarkdownCarrier()))
    cover = protected + '\n' + 'word ' * 200
    probe = build_probe(c.config, cover)
    assert probe.stego.startswith(protected)
    assert c.decode(c.encode(cover, b'x').text).payload == b'x'
