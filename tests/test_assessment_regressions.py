"""F1–F5 regression tests. Unsupported combinations/syntax fail explicitly."""
import pytest

from text_steganography import (
    ApostropheChannel, CanonicalUnicodeChannel, CodecConfig,
    CyrillicHomoglyphChannel, HtmlCarrier, MarkdownCarrier, SourceCodeCarrier,
    TextSteganographyCodec, UnicodeSpaceChannel, ZeroWidthChannel,
)
from text_steganography.config import FramingConfig, RepertoirePolicy
from text_steganography.errors import ConfigError
from text_steganography.probe import build_probe

def test_canonical_unicode_round_trips_hangul():
    codec = TextSteganographyCodec(CodecConfig(channels=[CanonicalUnicodeChannel()]))
    stego = codec.encode('가 ' * 150, b'hi').text
    assert codec.decode(stego).payload == b'hi'


def test_canonical_unicode_rejects_unstable_apostrophe_composition():
    with pytest.raises(ConfigError, match="site discovery is not stable"):
        TextSteganographyCodec(CodecConfig(
            channels=[CanonicalUnicodeChannel(), ApostropheChannel()],
        ))


def test_zero_width_reencoding_replaces_the_previous_payload():
    codec = TextSteganographyCodec(CodecConfig(channels=[ZeroWidthChannel()], repertoire=RepertoirePolicy(allow_joiners=True)))
    original = codec.encode('ab ' * 200, b'hi').text
    updated = codec.encode(original, b'yo').text
    assert codec.decode(updated).payload == b'yo'


def test_html_attribute_with_quoted_greater_than_is_untouched():
    codec = TextSteganographyCodec(CodecConfig(
        channels=[CyrillicHomoglyphChannel()], repertoire=RepertoirePolicy(allow_cross_script=True), carrier=HtmlCarrier(),
    ))
    cover = '<div title="> ' + 'a ' * 200 + '">body</div>'
    assert codec.analyze(cover).total_sites < 10


def test_markdown_entities_are_not_embedding_sites():
    codec = TextSteganographyCodec(CodecConfig(
        channels=[CyrillicHomoglyphChannel()], repertoire=RepertoirePolicy(allow_cross_script=True), carrier=MarkdownCarrier(),
    ))
    assert codec.analyze('&copy; ' * 200).total_sites == 0


def test_javascript_regexp_slashes_do_not_turn_a_string_into_a_comment():
    codec = TextSteganographyCodec(CodecConfig(
        channels=[UnicodeSpaceChannel()],
        carrier=SourceCodeCarrier.for_language('javascript'),
    ))
    # This valid JavaScript has a regexp and a string, but no comments.
    cover = 'const re = /[//]/; const text = "' + 'word ' * 200 + '";\n'
    with pytest.raises(ConfigError, match="regexp/division"):
        codec.analyze(cover)


def test_repertoire_rejects_cross_script_channel_without_permission():
    with pytest.raises(ConfigError):
        codec = TextSteganographyCodec(CodecConfig(channels=[CyrillicHomoglyphChannel()]))
        codec.encode('a' * 200, b'hi')


def test_channel_warnings_reach_analysis_and_encode_results():
    codec = TextSteganographyCodec(CodecConfig(channels=[ZeroWidthChannel()], repertoire=RepertoirePolicy(allow_joiners=True)))
    assert codec.analyze('ab ' * 200).warnings
    assert codec.encode('ab ' * 200, b'hi').warnings


@pytest.mark.parametrize('options', [
    {'schema_version': 999}, {'framing': FramingConfig('unknown')},
])
def test_unsupported_configuration_is_rejected(options):
    with pytest.raises(ConfigError):
        codec = TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()], **options))
        codec.encode('word ' * 200, b'hi')


def test_unrelated_excerpt_with_one_candidate_is_not_unique_evidence():
    codec = TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()]))
    result = codec.identify('unrelated', [b'hi'], cover_text='word ' * 200)
    assert result.known_bits == 0
    assert not result.unique


def test_probe_counts_only_carrier_eligible_sites():
    config = CodecConfig(channels=[UnicodeSpaceChannel()], carrier=HtmlCarrier())
    cover = '<div title="' + 'word ' * 100 + '">word word word word</div>'
    probe = build_probe(config, cover)
    # Every embedded mark is removed; untouched attribute spaces are irrelevant.
    report = probe.evaluate(probe.stego.replace('\u00a0', ' '))
    assert report.per_channel[0].survival_rate == 0.0
