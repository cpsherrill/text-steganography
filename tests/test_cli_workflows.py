"""File, pipe, and failure paths used by the documented command-line workflow."""
import io
import json
import unicodedata

import pytest

from text_steganography.cli.main import main


@pytest.mark.parametrize('arguments', [
    ['encode', '--text', 'x', '--channels', 'missing.channel'],
    ['encode', '--hex', 'not-hex'],
    ['encode', '--text', 'too large'],
])
def test_invalid_encode_does_not_create_an_output(arguments, tmp_path, capsys):
    cover = tmp_path / 'cover.txt'
    cover.write_text('short cover', encoding='utf-8')
    output = tmp_path / 'output.txt'
    assert main(arguments + ['-i', str(cover), '-o', str(output)]) == 2
    assert not output.exists()
    assert 'error:' in capsys.readouterr().err


def test_missing_input_returns_a_diagnostic(tmp_path, capsys):
    assert main(['analyze', '-i', str(tmp_path / 'missing.txt')]) == 2
    assert 'error:' in capsys.readouterr().err


def test_stdin_stdout_round_trip(monkeypatch, capsys):
    monkeypatch.setattr('sys.stdin', io.StringIO('word ' * 200))
    assert main(['encode', '--hex', 'ff00']) == 0
    stego = capsys.readouterr().out
    monkeypatch.setattr('sys.stdin', io.StringIO(stego))
    assert main(['decode', '--json']) == 0
    assert json.loads(capsys.readouterr().out)['payload_hex'] == 'ff00'


def test_saved_probe_survives_reload_and_detects_normalization(tmp_path, capsys):
    sample = tmp_path / 'sample.txt'
    metadata = tmp_path / 'probe.json'
    returned = tmp_path / 'returned.txt'
    assert main(['probe-make', '-o', str(sample), '--save', str(metadata)]) == 0
    capsys.readouterr()
    assert main(['probe-check', '--probe', str(metadata), '-i', str(sample), '--json']) == 0
    assert json.loads(capsys.readouterr().out)['overall_survival'] == 1.0
    returned.write_text(unicodedata.normalize('NFKC', sample.read_text(encoding='utf-8')), encoding='utf-8')
    assert main(['probe-check', '--probe', str(metadata), '-i', str(returned), '--json']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['overall_survival'] == 0.0
    assert report['per_channel'][0]['label'] == 'unsupported'


@pytest.mark.parametrize('capacity,expected_count,expected_log2', [
    (71, 0, None), (72, 1, 0), (80, 256, 8),
    (120, 2**48, 48), (128, None, 56), (16000, None, 15928),
])
def test_capacity_count_has_exact_bounded_json_representation(
    capacity, expected_count, expected_log2, monkeypatch, capsys,
):
    cover = ' '.join(['word'] * (capacity + 1))
    monkeypatch.setattr('sys.stdin', io.StringIO(cover))
    assert main(['analyze', '--json']) == 0
    result = json.loads(capsys.readouterr().out)
    assert result['max_distinct_payloads'] == expected_count
    assert result['max_distinct_payloads_log2'] == expected_log2
    monkeypatch.setattr('sys.stdin', io.StringIO(cover))
    assert main(['analyze']) == 0
    expected = str(expected_count) if expected_count is not None else f'2^{expected_log2}'
    assert f'distinct payloads:         {expected}\n' in capsys.readouterr().out


def test_large_capacity_under_strict_python_integer_limit():
    import os
    import subprocess
    import sys
    # Python 3.11+ (and patched older interpreters) honor this environment flag.
    # Do not disable or mutate the interpreter's protection to format a report.
    for flags in ([], ['--json']):
        result = subprocess.run(
            [sys.executable, '-m', 'text_steganography', 'analyze', *flags],
            input=' '.join(['word'] * 16001), text=True, capture_output=True,
            env={**os.environ, 'PYTHONINTMAXSTRDIGITS': '640'}, timeout=20,
        )
        assert result.returncode == 0, result.stderr
        assert len(result.stdout) < 2000
        if flags:
            report = json.loads(result.stdout)
            assert report['max_distinct_payloads'] is None
            assert report['max_distinct_payloads_log2'] == 15928
        else:
            assert '2^15928' in result.stdout
