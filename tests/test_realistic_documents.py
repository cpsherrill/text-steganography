"""Independent parser checks: prose spaces may change, document structure may not."""
import ast
from pathlib import Path

import html5lib
from markdown_it import MarkdownIt
import pytest

from text_steganography import (
    CodecConfig, ConfigError, HtmlCarrier, MarkdownCarrier, SourceCodeCarrier,
    TextSteganographyCodec, UnicodeSpaceChannel, build_probe,
)

FIXTURES = Path(__file__).parent / 'fixtures' / 'realistic'
PROSE = ' '.join(f'observation{i}' for i in range(200))


def codec(carrier):
    return TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()], carrier=carrier))


def normalized(text):
    # Only the configured space substitution is allowed, not general whitespace
    # folding or Unicode normalization that could hide unrelated corruption.
    return text.replace('\u00a0', ' ') if text is not None else None


def html_tree(document):
    def visit(node):
        text = node.text if node.tag in ('{http://www.w3.org/1999/xhtml}script',
                                        '{http://www.w3.org/1999/xhtml}style') else normalized(node.text)
        return (node.tag, sorted(node.attrib.items()), text,
                normalized(node.tail), tuple(visit(child) for child in node))
    return visit(html5lib.parse(document))


def markdown_tree(document):
    def visit(token):
        content = '' if token.children else token.content
        if token.type == 'text':
            content = normalized(content)
        elif token.type == 'html_block':
            content = html_tree(content)
        return (token.type, token.tag, token.nesting, token.attrs, token.info,
                token.markup, token.hidden, content,
                tuple(visit(child) for child in token.children or []))
    return tuple(visit(token) for token in MarkdownIt('commonmark').parse(document))


@pytest.mark.parametrize('filename,carrier,parse,suffix', [
    ('report.html', HtmlCarrier(), html_tree, '<p>' + PROSE + '</p>'),
    ('report.md', MarkdownCarrier(), markdown_tree, '\n\n' + PROSE),
    ('module.py', SourceCodeCarrier.for_language('python'),
     lambda source: ast.dump(ast.parse(source)), '\n# ' + PROSE + '\n'),
], ids=['html-report', 'markdown-report', 'python-module'])
def test_real_documents_preserve_independent_parse(filename, carrier, parse, suffix):
    cover = (FIXTURES / filename).read_text(encoding='utf-8') + suffix
    c = codec(carrier)
    baseline = parse(cover)
    marked = c.encode(cover, b'recipient-17').text
    assert c.decode(marked).payload == b'recipient-17'
    assert parse(marked) == baseline
    # A short payload leaves many zero-valued sites. Probe every site with a one
    # so protection checks exercise the entire fixture, including its tail.
    probe = build_probe(c.config, cover)
    assert parse(probe.stego) == baseline
    assert probe.evaluate(probe.stego).overall_survival == 1.0


@pytest.mark.parametrize('fragment', [
    '> quoted words\n>\n> ```python\n> literal code words\n> ```',
    '- list entry\n\n  ```python\n  literal code words\n  ```',
    'A hard break here  \ncontinues with *emphasis* and **strong words**.',
    '[a reference][key]\n\n[key]:\n  https://example.test/path\n  "multiline title words"',
    'A setext heading\n================\n\n---',
    '<div>\nraw HTML words\n</div>',
])
def test_markdown_structural_edge_cases(fragment):
    cover = fragment + '\n\n' + PROSE
    c = codec(MarkdownCarrier())
    marked = build_probe(c.config, cover).stego
    assert markdown_tree(marked) == markdown_tree(cover)


@pytest.mark.parametrize('fragment', [
    '<p title="quoted > words">ordinary words</p>',
    '<!-- unclosed words with spaces',
    '<script/>const s = "protected literal words";</script>',
    '<textarea>literal words &amp; markup</textarea>',
    '<svg><text>some visible words</text></svg>',
])
def test_html_edge_cases_preserve_tree(fragment):
    cover = '<p>' + PROSE + '</p>' + fragment
    c = codec(HtmlCarrier())
    marked = build_probe(c.config, cover).stego
    assert html_tree(marked) == html_tree(cover)


@pytest.mark.parametrize('source', [
    'value = "unterminated\n# ordinary words',
    'value = """unterminated\n# ordinary words',
    'if True:\n  pass\n pass\n# ordinary words',
])
def test_malformed_python_cannot_be_encoded(source):
    with pytest.raises(ConfigError):
        codec(SourceCodeCarrier.for_language('python')).encode(source + '\n# ' + PROSE, b'x')
