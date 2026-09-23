"""Report core timings on deterministic inputs; no machine-dependent pass threshold."""
import json
import platform
import time
from text_steganography import CodecConfig, TextSteganographyCodec, UnicodeSpaceChannel, build_probe

codec = TextSteganographyCodec(CodecConfig(channels=[UnicodeSpaceChannel()]))
rows = []
for capacity in (2000, 16000, 64000):
    cover = ' '.join(['word'] * (capacity + 1))
    payload = bytes([255]) * ((capacity - 72) // 8)
    timings = {}
    def measure(name, function):
        start = time.perf_counter()
        value = function()
        timings[name] = round(time.perf_counter() - start, 4)
        return value
    report = measure('analyze_seconds', lambda: codec.analyze(cover))
    marked = measure('encode_seconds', lambda: codec.encode(cover, payload).text)
    decoded = measure('decode_seconds', lambda: codec.decode(marked))
    probe = measure('probe_build_seconds', lambda: build_probe(codec.config, cover))
    assert decoded.payload == payload and probe.evaluate(probe.stego).overall_survival == 1
    rows.append({'sites': capacity, 'cover_characters': len(cover), 'payload_bytes': len(payload), **timings})
print(json.dumps({'platform': platform.platform(), 'python': platform.python_version(),
                  'method': 'one run per size, no timing assertion', 'results': rows}, indent=2))
