"""Record actual local transport evidence; never sends data to an external service.

Run with an installed checkout: python scripts/validate_local_transports.py OUTPUT
Use --clipboard-helper /path/to/compiled/helper for a macOS pasteboard round trip.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import zipfile

from text_steganography import (
    ApostropheChannel, CodecConfig, TextSteganographyCodec, UnicodeSpaceChannel,
    build_probe,
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--clipboard-helper', type=Path)
    args = parser.parse_args()
    # Refuse overwrite: each directory is an immutable experiment record.
    args.output.mkdir(parents=True, exist_ok=False)
    config = CodecConfig(channels=[UnicodeSpaceChannel(), ApostropheChannel()])
    codec = TextSteganographyCodec(config)
    cover = '\n'.join(
        f"Observation {i}: it's useful to keep the original file because we can't "
        "infer transport behavior from a different application or a different route."
        for i in range(40)
    ) + '\n'
    payload = b'recipient-17'
    probe = build_probe(config, cover)
    (args.output / 'cover.txt').write_text(cover, encoding='utf-8')
    (args.output / 'config.json').write_text(json.dumps(config.to_dict(), indent=2)+'\n')
    (args.output / 'probe.json').write_text(json.dumps(probe.to_dict(), indent=2)+'\n')
    candidates = [b'recipient-16', payload, b'recipient-18']
    sources = {'payload': codec.encode(cover, payload).text, 'probe': probe.stego}
    routes = ['file_copy', 'zip_extract', 'subprocess_pipe']
    if args.clipboard_helper:
        routes.append('macos_plaintext_pasteboard')
    results = []
    for route in routes:
        folder = args.output / route
        folder.mkdir()
        returned = {}
        records = {}
        for kind, text in sources.items():
            data = text.encode('utf-8')
            source, target = folder / f'{kind}.sent.txt', folder / f'{kind}.returned.txt'
            source.write_bytes(data)
            if route == 'file_copy':
                shutil.copyfile(source, target)
            elif route == 'zip_extract':
                archive = folder / f'{kind}.zip'
                with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
                    zipped.write(source, 'sample.txt')
                with zipfile.ZipFile(archive) as zipped:
                    target.write_bytes(zipped.read('sample.txt'))
            elif route == 'subprocess_pipe':
                proc = subprocess.run(
                    [sys.executable, '-c', 'import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())'],
                    input=data, capture_output=True, check=True, timeout=20,
                )
                target.write_bytes(proc.stdout)
            else:
                subprocess.run([str(args.clipboard_helper.resolve()), str(source), str(target)],
                               check=True, timeout=20)
            actual = target.read_bytes()
            returned[kind] = actual.decode('utf-8')
            records[kind] = {'sent_sha256': digest(data), 'returned_sha256': digest(actual),
                             'byte_identical': data == actual}
        decoded = codec.decode(returned['payload'])
        found = codec.identify(returned['payload'], candidates)
        survival = probe.evaluate(returned['probe'])
        results.append({'route': route, 'samples': records,
                        'decode_status': decoded.status.value,
                        'payload_matches': decoded.payload == payload,
                        'unique_correct_candidate': found.unique and found.best().payload == payload,
                        'probe_survival': survival.overall_survival,
                        'probe_summary': survival.summary()})
    metadata = {'recorded_at': datetime.now(timezone.utc).isoformat(),
                'platform': platform.platform(), 'macos': platform.mac_ver()[0],
                'python': platform.python_version(),
                'git_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                'working_tree_dirty': bool(subprocess.check_output(['git', 'status', '--porcelain'])),
                'codec_id': codec.codec_id, 'payload_hex': payload.hex(),
                'scope': 'Local OS paths only; no email/chat/editor/cloud-service delivery measured.',
                'results': results}
    (args.output / 'results.json').write_text(json.dumps(metadata, indent=2)+'\n')
    print(json.dumps(metadata, indent=2))
    return 0 if all(row['payload_matches'] and row['unique_correct_candidate']
                    and row['probe_survival'] == 1 for row in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
