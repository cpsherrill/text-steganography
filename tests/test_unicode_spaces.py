from __future__ import annotations

from text_steganography.channels.whitespace import UnicodeSpaceChannel
from text_steganography.models import ObservationState

_SPACE = "\u0020"
_NBSP = "\u00a0"


def test_discovers_single_inter_word_spaces():
    channel = UnicodeSpaceChannel()
    sites = channel.discover_sites("one two three")
    assert len(sites) == 2
    assert [s.ordinal for s in sites] == [0, 1]
    assert all(s.radix == 2 for s in sites)


def test_skips_leading_trailing_and_double_spaces():
    channel = UnicodeSpaceChannel()
    # leading, trailing, and a double space are all ineligible
    assert channel.discover_sites("  a  b  ") == []
    assert len(channel.discover_sites("a b")) == 1


def test_observe_reads_variants():
    channel = UnicodeSpaceChannel()
    text = "a" + _NBSP + "b" + _SPACE + "c"
    observations = channel.observe(text)
    assert [o.symbol for o in observations] == [1, 0]
    assert all(o.state is ObservationState.KNOWN for o in observations)


def test_canonicalize_restores_plain_spaces():
    channel = UnicodeSpaceChannel()
    stego = "the" + _NBSP + "quick" + _NBSP + "fox"
    assert channel.canonicalize(stego) == "the quick fox"


def test_site_count_is_stable_between_cover_and_stego():
    channel = UnicodeSpaceChannel()
    cover = "alpha beta gamma delta"
    # a stegotext where the first two spaces became no-break spaces
    stego = cover.replace(" ", _NBSP, 2)
    # the property decoding relies on: the site count does not change
    assert len(channel.discover_sites(cover)) == len(channel.discover_sites(stego))


def test_metadata_is_honest_about_fragility():
    meta = UnicodeSpaceChannel().metadata()
    assert meta.channel_id == "whitespace.unicode_space"
    assert meta.warnings  # it must warn; this channel is fragile by nature
