from __future__ import annotations

from text_steganography import inspect_text

_NBSP = "\u00a0"
_ZWSP = "\u200b"
_CYRILLIC_A = "\u0430"  # looks like Latin 'a'
_COMBINING_ACUTE = "\u0301"


def test_plain_ascii_is_unremarkable():
    report = inspect_text("the quick brown fox")
    assert report.notable == ()
    assert report.scripts == ("Latin",)
    assert report.mixed_scripts is False
    assert report.nfc_differs is False


def test_flags_no_break_space():
    report = inspect_text("a" + _NBSP + "b")
    assert len(report.notable) == 1
    note = report.notable[0]
    assert note.codepoint == "U+00A0"
    assert note.note == "non-standard space"


def test_flags_zero_width_character():
    report = inspect_text("word" + _ZWSP + "word")
    assert any(n.codepoint == "U+200B" for n in report.notable)
    assert any(n.note == "invisible or control character" for n in report.notable)


def test_detects_mixed_scripts():
    report = inspect_text("a" + _CYRILLIC_A)
    assert report.mixed_scripts is True
    assert "Latin" in report.scripts and "Cyrillic" in report.scripts


def test_detects_normalization_difference():
    # 'e' + combining acute accent differs from its composed form under NFC
    report = inspect_text("cafe" + _COMBINING_ACUTE)
    assert report.nfc_differs is True


def test_summary_is_a_readable_string():
    report = inspect_text("a" + _NBSP + "b" + _CYRILLIC_A)
    summary = report.summary()
    assert "notable" in summary
    assert "MIXED SCRIPTS" in summary
