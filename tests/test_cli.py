from __future__ import annotations

import json

from text_steganography.cli.main import main


def cover() -> str:
    return " ".join(["word"] * 200)


def test_cli_encode_then_decode_round_trip(tmp_path, capsys):
    cover_file = tmp_path / "cover.txt"
    cover_file.write_text(cover(), encoding="utf-8")
    stego_file = tmp_path / "stego.txt"

    rc = main(["encode", "-i", str(cover_file), "-o", str(stego_file), "--text", "hello"])
    assert rc == 0
    capsys.readouterr()  # drain

    rc = main(["decode", "-i", str(stego_file)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "status:          success" in out
    assert "hello" in out


def test_cli_encode_hex_payload(tmp_path, capsys):
    cover_file = tmp_path / "cover.txt"
    cover_file.write_text(cover(), encoding="utf-8")
    stego_file = tmp_path / "stego.txt"

    assert main(["encode", "-i", str(cover_file), "-o", str(stego_file), "--hex", "0a1b2c"]) == 0
    capsys.readouterr()
    assert main(["decode", "-i", str(stego_file), "--json"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "success"
    assert result["payload_hex"] == "0a1b2c"


def test_cli_analyze_json(tmp_path, capsys):
    cover_file = tmp_path / "cover.txt"
    cover_file.write_text(" ".join(["word"] * 100), encoding="utf-8")

    assert main(["analyze", "-i", str(cover_file), "--json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["total_sites"] == 99
    assert report["usable_payload_bytes"] == 3


def test_cli_inspect_flags_nbsp(tmp_path, capsys):
    text_file = tmp_path / "t.txt"
    text_file.write_text("a\u00a0b", encoding="utf-8")

    assert main(["inspect", "-i", str(text_file)]) == 0
    out = capsys.readouterr().out
    assert "U+00A0" in out


def test_cli_decode_plain_text_returns_nonzero(tmp_path, capsys):
    cover_file = tmp_path / "cover.txt"
    cover_file.write_text(cover(), encoding="utf-8")

    rc = main(["decode", "-i", str(cover_file)])
    assert rc == 1  # no payload recovered
