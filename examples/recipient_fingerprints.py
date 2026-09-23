"""Create marked copies, reload the configuration, and identify an excerpt."""
import json

from text_steganography import CodecConfig, TextSteganographyCodec, UnicodeSpaceChannel


def main():
    # Unique words make the excerpt's position unambiguous. This is a synthetic
    # capacity/alignment fixture, not evidence about a real delivery service.
    cover = ' '.join('word{}'.format(i) for i in range(240))
    config = CodecConfig(channels=[UnicodeSpaceChannel()])
    codec = TextSteganographyCodec(config)
    recipients = [bytes([i]) for i in range(30)]  # opaque demonstration tokens
    assert codec.preflight(cover, recipients).ok
    copies = codec.encode_many(cover, recipients)

    # In an application, retain this configuration and the token-to-recipient map.
    saved_config = json.dumps(config.to_dict())
    reader = TextSteganographyCodec(CodecConfig.from_dict(json.loads(saved_config)))
    leaked_copy = copies[17].text
    assert reader.decode(leaked_copy).payload == recipients[17]
    assert reader.canonicalize(leaked_copy) == cover

    excerpt = leaked_copy[40:700]
    alignment = reader.align_excerpt(cover, excerpt)
    assert alignment.aligned
    result = reader.identify(excerpt, recipients, cover_text=cover)
    # unique now requires known evidence; keep this check explicit in the example.
    assert result.known_bits > 0 and result.unique
    assert result.best().payload == recipients[17]
    print('Full copy decoded; excerpt identifies token 17 among 30 candidates.')
    print('Evidence: {} known bits; this is not a probability of attribution.'.format(result.known_bits))


if __name__ == '__main__':
    main()
