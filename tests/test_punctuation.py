from __future__ import annotations

from text_steganography.channels.punctuation import ApostropheChannel
from text_steganography.models import ObservationState

_STRAIGHT = "\u0027"
_CURLY = "\u2019"


def test_discovers_contraction_apostrophes_only():
    channel = ApostropheChannel()
    # two contractions, and a leading quote that must NOT be a site
    sites = channel.discover_sites("it's a dog's " + _STRAIGHT + "quote")
    assert len(sites) == 2
    assert all(s.radix == 2 for s in sites)


def test_observe_reads_variants():
    channel = ApostropheChannel()
    text = "it" + _CURLY + "s and don" + _STRAIGHT + "t"
    observations = channel.observe(text)
    assert [o.symbol for o in observations] == [1, 0]
    assert all(o.state is ObservationState.KNOWN for o in observations)


def test_canonicalize_restores_straight_apostrophes():
    channel = ApostropheChannel()
    stego = "it" + _CURLY + "s a cat" + _CURLY + "s toy"
    assert channel.canonicalize(stego) == "it's a cat's toy"


def test_metadata_admits_it_is_not_invisible():
    meta = ApostropheChannel().metadata()
    assert meta.channel_id == "punctuation.apostrophe"
    assert any("not invisible" in w for w in meta.warnings)
