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
