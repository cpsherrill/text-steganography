"""Cross-layer regressions for F1–F5, beyond their original reproductions."""
from itertools import combinations, permutations
import json
import sys
import unicodedata

import pytest
from hypothesis import given, settings, strategies as st

from text_steganography import (
    ApostropheChannel, CanonicalUnicodeChannel, CodecConfig, ConfigError,
    CyrillicHomoglyphChannel, HtmlCarrier, MarkdownCarrier, RepertoirePolicy,
    SourceCodeCarrier, TextSteganographyCodec, UnicodeSpaceChannel,
    ZeroWidthChannel, build_probe,
)
from text_steganography.cli.main import main
from text_steganography.probe import Probe, SurvivalLabel

PERMISSIONS = RepertoirePolicy(allow_cross_script=True, allow_joiners=True)


def codec(channels, carrier=None):
    kwargs = {'carrier': carrier} if carrier is not None else {}
    return TextSteganographyCodec(CodecConfig(channels=channels, repertoire=PERMISSIONS, **kwargs))


def test_every_canonical_decomposition_pair_is_rediscoverable():
    channel = CanonicalUnicodeChannel()
    checked = 0
    for codepoint in range(sys.maxunicode + 1):
        composed = chr(codepoint)
        decomposed = unicodedata.normalize('NFD', composed)
        if len(decomposed) <= 1 or unicodedata.normalize('NFC', decomposed) != composed:
            continue
        checked += 1
        for text, symbol in [(composed, 0), (decomposed, 1)]:
            sites = channel.discover_sites(text)
            observations = channel.observe(text)
            assert len(sites) == len(observations) == 1, hex(codepoint)
            assert observations[0].symbol == symbol, hex(codepoint)
            assert sites[0].variants == (composed, decomposed)
    assert checked > 12000


@settings(max_examples=40, deadline=None)
@given(st.lists(st.sampled_from(['é', 'Å', '가', '각', 'ώ', 'ো', 'é\u0300']), min_size=100, max_size=120),
       st.binary(max_size=2), st.booleans())
def test_unicode_cover_round_trip_and_reencoding(characters, payload, decompose):
    cover = ' '.join(characters)
    if decompose:
        cover = unicodedata.normalize('NFD', cover)
    channels = [UnicodeSpaceChannel(), CanonicalUnicodeChannel()]
    if decompose:
        channels.reverse()  # exercise canonical sites carrying payload bits too
    c = codec(channels)
    marked = c.encode(cover, payload).text
    assert c.decode(marked).payload == payload
    assert unicodedata.normalize('NFC', c.canonicalize(marked)) == unicodedata.normalize('NFC', cover)
    assert c.decode(c.encode(marked, b'x').text).payload == b'x'


SAFE_CLASSES = [UnicodeSpaceChannel, ApostropheChannel, CyrillicHomoglyphChannel, ZeroWidthChannel]
COMBINATIONS = [order for size in range(1, 5)
                for group in combinations(SAFE_CLASSES, size) for order in permutations(group)]


@pytest.mark.parametrize('channel_types', COMBINATIONS,
                         ids=lambda types: '+'.join(t.__name__ for t in types))
def test_supported_channel_combinations_preserve_discovery(channel_types):
    c = codec([kind() for kind in channel_types])
    cover = "cacao it's can't people " * 65
    marked = c.encode(cover, b'first').text
    assert c.decode(marked).payload == b'first'
    assert c.decode(c.encode(marked, b'next').text).payload == b'next'
    assert c.canonicalize(marked) == cover
    probe = build_probe(c.config, cover)
    assert probe.evaluate(probe.stego).overall_survival == 1.0


@pytest.mark.parametrize('other', [ApostropheChannel, CyrillicHomoglyphChannel, ZeroWidthChannel])
@pytest.mark.parametrize('reverse', [False, True])
def test_incompatible_unicode_combinations_fail_before_planning(other, reverse):
    channels = [CanonicalUnicodeChannel(), other()]
    if reverse:
        channels.reverse()
    with pytest.raises(ConfigError, match='site discovery is not stable'):
        codec(channels)


@pytest.mark.parametrize('protected', [
    '<a title="quoted > ' + 'a ' * 90 + '">',
    "<a title='quoted > " + 'a ' * 90 + "'>",
    '<!-- comment > ' + 'a ' * 90 + ' -->',
    '<script>const text = "' + 'a ' * 90 + '";</script>',
    '<style>/* ' + 'a ' * 90 + ' */</style>',
    '&copy; &#233; &#xE9;',
])
def test_html_protected_content_survives_all_safe_channels(protected):
    c = codec([CyrillicHomoglyphChannel(), ZeroWidthChannel(), UnicodeSpaceChannel()], HtmlCarrier())
    cover = protected + '<p>' + 'cacao people ' * 100 + '</p>'
    marked = c.encode(cover, b'html').text
    assert marked.startswith(protected + '<p>')
    assert c.decode(marked).payload == b'html'


@pytest.mark.parametrize('cover', ['<div title="unclosed > a a a', '<!-- unclosed > a a a'])
def test_unfinished_html_is_not_treated_as_prose(cover):
    assert codec([UnicodeSpaceChannel()], HtmlCarrier()).analyze(cover).total_sites == 0


@pytest.mark.parametrize('protected', [
    '&copy; &#233; &#xE9;',
    '[copy][reference]\n\n[reference]: https://example.test/a\n',
    '[shortcut]\n\n[shortcut]: https://example.test/a\n',
    '[text](https://example.test/a(b)c "quoted ) title")',
    '``code ` with a single backtick and spaces``',
    '<!-- markup > comment -->',
    '<a title="quoted > attribute">',
])
def test_markdown_protected_regions_remain_byte_identical(protected):
    c = codec([CyrillicHomoglyphChannel(), UnicodeSpaceChannel()], MarkdownCarrier())
    cover = protected + '\n\n' + 'cacao people ' * 100
    marked = c.encode(cover, b'md').text
    assert marked.startswith(protected)
    assert c.decode(marked).payload == b'md'


def test_python_tokenizer_handles_escaped_triple_quotes_and_directives():
    import ast
    protected = ('#!/usr/bin/env python\n# coding: utf-8\n'
                 'text = """escaped \\""" # this remains string content\nmore words"""\n')
    c = codec([UnicodeSpaceChannel()], SourceCodeCarrier.for_language('python'))
    cover = protected + '# ' + 'comment words ' * 100 + '\n'
    marked = c.encode(cover, b'py').text
    assert marked.startswith(protected)
    assert ast.dump(ast.parse(marked)) == ast.dump(ast.parse(cover))
    assert c.decode(marked).payload == b'py'


@pytest.mark.parametrize('source', ['const r = /[//]/;', 'const n = a / b;', 'const t = `a ${b}`;'])
def test_unsupported_javascript_syntax_is_rejected(source):
    with pytest.raises(ConfigError):
        codec([UnicodeSpaceChannel()], SourceCodeCarrier.for_language('javascript')).analyze(source)


def test_simple_javascript_comments_and_strings_are_preserved():
    protected = 'const value = "// this is a string";\n'
    cover = protected + '// ' + 'comment words ' * 100
    c = codec([UnicodeSpaceChannel()], SourceCodeCarrier.for_language('javascript'))
    marked = c.encode(cover, b'js').text
    assert marked.startswith(protected)
    assert c.decode(marked).payload == b'js'


def test_c_line_splicing_is_rejected():
    with pytest.raises(ConfigError, match='continuations'):
        codec([UnicodeSpaceChannel()], SourceCodeCarrier.for_language('c')).analyze('// a\\\nb\n')


@pytest.mark.parametrize('channel,permission', [
    (ZeroWidthChannel, 'allow_joiners'), (CyrillicHomoglyphChannel, 'allow_cross_script'),
])
def test_risky_channels_require_permissions_even_from_serialized_configuration(channel, permission):
    config = CodecConfig(channels=[channel()])
    with pytest.raises(ConfigError, match=permission):
        CodecConfig.from_dict(config.to_dict())
    permitted = CodecConfig(channels=[channel()], repertoire=RepertoirePolicy(**{permission: True}))
    assert CodecConfig.from_dict(permitted.to_dict()).codec_id == permitted.codec_id


def test_configuration_snapshot_cannot_be_mutated_by_callers():
    original = CodecConfig(channels=[UnicodeSpaceChannel()])
    c = TextSteganographyCodec(original)
    identifier = c.codec_id
    original.channels.clear()
    c.config.channels.clear()
    cover = 'word ' * 200
    assert c.codec_id == identifier
    assert c.decode(c.encode(cover, b'ok').text).payload == b'ok'


@pytest.mark.parametrize('flags', [{'allow_joiners': 'false'}, {'allow_cross_script': 1}])
def test_nonboolean_permissions_are_not_coerced_to_true(flags):
    data = CodecConfig(channels=[UnicodeSpaceChannel()]).to_dict()
    data['repertoire'].update(flags)
    with pytest.raises(ConfigError, match='boolean'):
        CodecConfig.from_dict(data)


@pytest.mark.parametrize('channels', [[], [UnicodeSpaceChannel(), UnicodeSpaceChannel()]])
def test_empty_and_duplicate_channels_are_rejected(channels):
    with pytest.raises(ConfigError):
        codec(channels)


def test_cli_risky_opt_in_and_warnings(tmp_path, capsys):
    cover = tmp_path / 'cover.txt'
    cover.write_text('ab ' * 200, encoding='utf-8')
    args = ['analyze', '-i', str(cover), '--channels', 'invisible.zero_width', '--json']
    assert main(args) == 2
    assert 'allow_joiners' in capsys.readouterr().err
    assert main(args + ['--allow-joiners']) == 0
    assert json.loads(capsys.readouterr().out)['warnings']
    out = tmp_path / 'stego.txt'
    assert main(['encode', '-i', str(cover), '-o', str(out), '--text', 'x',
                 '--channels', 'invisible.zero_width', '--allow-joiners']) == 0
    assert 'warning:' in capsys.readouterr().err


@pytest.mark.parametrize('excerpt,expected', [('unrelated', 'not_found'), ('word word', 'ambiguous')])
def test_identification_preserves_failed_alignment(excerpt, expected):
    c = codec([UnicodeSpaceChannel()])
    result = c.identify(excerpt, [b'x'], cover_text='word ' * 200)
    assert result.status == result.alignment.status == expected
    assert result.known_bits == 0 and not result.unique
    assert result.best() is None


def test_unsupported_excerpt_alignment_is_preserved_in_identification():
    result = codec([ZeroWidthChannel()]).identify('ab', [b'x'], cover_text='ab ' * 200)
    assert result.status == 'unsupported'
    assert not result.unique and result.best() is None


def test_contradictory_best_candidate_is_not_a_unique_match():
    result = codec([UnicodeSpaceChannel()]).identify('word ' * 200, [b'x'])
    assert result.status == 'contradictory'
    assert not result.unique
    assert result.best() is not None and not result.best().consistent


@pytest.mark.parametrize('carrier,protected,body', [
    (HtmlCarrier(), '<a title="' + 'word ' * 100 + '">', 'word word word</a>'),
    (MarkdownCarrier(), '`' + 'word ' * 100 + '`\n\n', 'word word word'),
    (SourceCodeCarrier.for_language('python'), 'value = "' + 'word ' * 100 + '"\n', '# word word word'),
])
def test_probes_and_codec_count_the_same_sites(carrier, protected, body):
    c = codec([UnicodeSpaceChannel()], carrier)
    cover = protected + body
    probe = build_probe(c.config, cover)
    assert probe.stego.startswith(protected)
    assert len(probe.expected[UnicodeSpaceChannel.id]) == c.analyze(cover).total_sites
    assert Probe.from_dict(probe.to_dict()).evaluate(probe.stego).overall_survival == 1
    erased = probe.evaluate(probe.stego.replace('\u00a0', ' '))
    assert erased.overall_survival == 0
    assert erased.per_channel[0].label is SurvivalLabel.UNSUPPORTED


def test_old_probe_expectations_are_rebuilt_with_carrier_filtering():
    probe = build_probe(codec([UnicodeSpaceChannel()], HtmlCarrier()).config,
                        '<a title="word word word">word word</a>')
    saved = probe.to_dict()
    saved.pop('probe_version')
    saved['expected'] = {UnicodeSpaceChannel.id: [0, 0, 1]}
    restored = Probe.from_dict(saved)
    assert restored.expected == probe.expected
    assert restored.evaluate(restored.stego.replace('\u00a0', ' ')).overall_survival == 0


def test_corrupt_current_probe_expectations_are_rejected():
    saved = build_probe(codec([UnicodeSpaceChannel()]).config).to_dict()
    saved['expected'] = {}
    with pytest.raises(ConfigError, match='expectations'):
        Probe.from_dict(saved)


def test_probe_site_count_change_does_not_recommend_a_transport():
    probe = build_probe(codec([UnicodeSpaceChannel()]).config)
    report = probe.evaluate(probe.stego + ' extra word')
    assert report.per_channel[0].site_delta != 0
    assert report.per_channel[0].label is SurvivalLabel.UNTESTED


@pytest.mark.parametrize('carrier,protected,body', [
    (HtmlCarrier(), '<p title="keep\u00a0space">', 'word ' * 200 + '</p>'),
    (MarkdownCarrier(), '`keep\u00a0space`\n\n', 'word ' * 200),
    (SourceCodeCarrier.for_language('python'), 's = "keep\u00a0space"\n', '# ' + 'word ' * 200),
])
def test_canonicalization_also_respects_carrier_boundaries(carrier, protected, body):
    c = codec([UnicodeSpaceChannel()], carrier)
    cover = protected + body
    marked = c.encode(cover, b'keep').text
    assert c.canonicalize(marked) == cover


def test_source_excerpt_is_aligned_using_original_document_context():
    cover = '# ' + ' '.join('word{}'.format(i) for i in range(240)) + '\n'
    c = codec([UnicodeSpaceChannel()], SourceCodeCarrier.for_language('python'))
    marked = c.encode(cover, b'x').text
    result = c.identify(marked[40:700], [b'x', b'y'], cover_text=cover)
    assert result.unique and result.alignment.aligned
    assert result.best().payload == b'x'


class _DriftingSpaceChannel(UnicodeSpaceChannel):
    id = 'test.drifting_space'

    def observe(self, text, context=None):
        return super().observe(text, context)[1:]


def test_encoding_and_probes_reject_unstable_plugin_observations():
    c = codec([_DriftingSpaceChannel()])
    with pytest.raises(ConfigError, match='changes site discovery'):
        c.encode('word ' * 200, b'x')
    with pytest.raises(ConfigError, match='changes site discovery'):
        build_probe(c.config, 'word ' * 200)


def test_unknown_packing_is_rejected_by_constructor_and_deserializer():
    with pytest.raises(ConfigError, match='packing'):
        TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()], packing='unknown'))
    data = CodecConfig(channels=[UnicodeSpaceChannel()]).to_dict()
    data['packing'] = 'unknown'
    with pytest.raises(ConfigError, match='packing'):
        CodecConfig.from_dict(data)


def test_probe_does_not_report_a_percentage_when_sites_cannot_be_aligned():
    probe = build_probe(codec([UnicodeSpaceChannel()]).config)
    report = probe.evaluate(probe.stego + ' extra word')
    assert report.overall_survival is None
    assert report.per_channel[0].survival_rate is None
    assert 'unmeasured' in report.summary()


@pytest.mark.parametrize('source', ['text = "unterminated', 'text = """unterminated'])
def test_malformed_python_does_not_offer_comment_capacity(source):
    with pytest.raises(ConfigError):
        codec([UnicodeSpaceChannel()], SourceCodeCarrier.for_language('python')).analyze(source)


@pytest.mark.parametrize('carrier', [HtmlCarrier(), MarkdownCarrier(), SourceCodeCarrier.for_language('python')])
def test_old_carrier_versions_are_rejected_instead_of_reinterpreted(carrier):
    data = CodecConfig(channels=[UnicodeSpaceChannel()], carrier=carrier).to_dict()
    data['carrier']['version'] = '1'
    with pytest.raises(ConfigError, match='version mismatch'):
        CodecConfig.from_dict(data)


@pytest.mark.parametrize('channel', [CanonicalUnicodeChannel(), ZeroWidthChannel()])
def test_changed_scanners_have_explicit_version_boundaries(channel):
    data = CodecConfig(channels=[channel], repertoire=PERMISSIONS).to_dict()
    data['channels'][0]['version'] = '1'
    with pytest.raises(ConfigError, match='version mismatch'):
        CodecConfig.from_dict(data)
