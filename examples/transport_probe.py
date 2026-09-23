"""Measure two deterministic transformations; no external service is contacted."""
import unicodedata

from text_steganography import ApostropheChannel, CodecConfig, UnicodeSpaceChannel
from text_steganography.probe import build_probe
from text_steganography.profiles import profile_from_probe


def main():
    config = CodecConfig(channels=[UnicodeSpaceChannel(), ApostropheChannel()])
    probe = build_probe(config)
    intact = probe.evaluate(probe.stego)
    assert intact.overall_survival == 1.0
    print('Unchanged text:', intact.summary())

    normalized = probe.evaluate(unicodedata.normalize('NFKC', probe.stego))
    by_channel = {item.channel_id: item for item in normalized.per_channel}
    assert by_channel['whitespace.unicode_space'].survival_rate == 0.0
    assert by_channel['punctuation.apostrophe'].survival_rate == 1.0
    print('NFKC normalization:', normalized.summary())
    profile = profile_from_probe(
        'example_nfkc', 'Synthetic NFKC normalization', probe,
        unicodedata.normalize('NFKC', probe.stego),
        evidence='Local synthetic NFKC transform; no external transport measured',
    )
    assert profile.warnings_for(config)
    print('Profile warnings:', '; '.join(profile.warnings_for(config)))


if __name__ == '__main__':
    main()
