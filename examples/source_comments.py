"""Fingerprint a simple Python comment, then compare program syntax trees."""
import ast

from text_steganography import CodecConfig, SourceCodeCarrier, TextSteganographyCodec, UnicodeSpaceChannel


def main():
    cover = (
        '# ' + ' '.join('note{}'.format(i) for i in range(200)) + '\n'
        'message = "This string must remain byte-identical."\n'
        'def add(a, b):\n'
        '    return a + b\n'
    )
    codec = TextSteganographyCodec(CodecConfig(
        channels=[UnicodeSpaceChannel()],
        carrier=SourceCodeCarrier.for_language('python'),
    ))
    stego = codec.encode(cover, b'r17').text
    assert codec.decode(stego).payload == b'r17'
    assert stego.split('\n', 1)[1] == cover.split('\n', 1)[1]
    assert ast.dump(ast.parse(stego)) == ast.dump(ast.parse(cover))
    print('Token r17 recovered; code and strings unchanged; Python syntax trees match.')
    print('This simple fixture does not establish safety for arbitrary source code.')


if __name__ == '__main__':
    main()
