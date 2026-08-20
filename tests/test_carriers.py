from __future__ import annotations

from text_steganography.carriers import (
    HtmlCarrier,
    PlainTextCarrier,
    invert_spans,
    merge_spans,
    site_in_spans,
)


def texts_in(document: str, spans):
    return [document[s:e] for s, e in spans]


def test_plain_text_carrier_is_the_whole_document():
    doc = "hello world"
    assert PlainTextCarrier().safe_spans(doc) == [(0, len(doc))]
    assert PlainTextCarrier().safe_spans("") == []


def test_merge_and_invert_spans():
    assert merge_spans([(0, 2), (1, 3), (5, 6)]) == [(0, 3), (5, 6)]
    assert invert_spans([(2, 4)], 8) == [(0, 2), (4, 8)]
    assert invert_spans([], 5) == [(0, 5)]
    assert invert_spans([(0, 5)], 5) == []


def test_site_in_spans():
    spans = [(0, 4), (10, 20)]
    assert site_in_spans(1, 2, spans) is True
    assert site_in_spans(3, 5, spans) is False  # straddles the gap
    assert site_in_spans(10, 11, spans) is True


def test_html_carrier_excludes_tags():
    doc = "<p>hello world</p>"
    spans = HtmlCarrier().safe_spans(doc)
    assert texts_in(doc, spans) == ["hello world"]


def test_html_carrier_excludes_attributes_and_urls():
    doc = '<a href="http://example.com/secret">click here</a>'
    spans = HtmlCarrier().safe_spans(doc)
    joined = "".join(texts_in(doc, spans))
    assert "click here" in joined
    assert "example.com" not in joined  # the URL lives in an attribute, off limits


def test_html_carrier_excludes_script_and_style_contents():
    doc = "<style>a{color:red}</style><p>text</p><script>var x=1;</script>"
    spans = HtmlCarrier().safe_spans(doc)
    joined = "".join(texts_in(doc, spans))
    assert "text" in joined
    assert "color:red" not in joined
    assert "var x" not in joined


def test_html_carrier_excludes_entities():
    doc = "<p>a &amp; b</p>"
    spans = HtmlCarrier().safe_spans(doc)
    joined = "".join(texts_in(doc, spans))
    assert "&amp;" not in joined
    # the letters around the entity are still safe
    assert "a " in joined and " b" in joined
