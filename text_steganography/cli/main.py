"""The ``tsteg`` command-line interface.

Four subcommands mirror the library workflow: ``analyze``, ``encode``,
``decode``, and ``inspect``. Text is read from a file or standard input and
written to a file or standard output, so the tool composes with pipes. The
codec is chosen with ``--channels``, a comma-separated list of channel ids.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import List, Optional

from ..channels.base import get_channel_class
from ..codec import TextSteganographyCodec
from ..config import CodecConfig
from ..ecc import NoErrorCorrection, RepetitionCode
from ..errors import TextSteganographyError
from ..inspect import inspect_text

DEFAULT_CHANNELS = "whitespace.unicode_space"


def _build_codec(channels_arg: str, ecc_repeat: int = 1) -> TextSteganographyCodec:
    ids = [part.strip() for part in channels_arg.split(",") if part.strip()]
    if not ids:
        raise TextSteganographyError("no channels specified")
    channels = [get_channel_class(channel_id)() for channel_id in ids]
    error_correction = RepetitionCode(repeat=ecc_repeat) if ecc_repeat > 1 else NoErrorCorrection()
    return TextSteganographyCodec(
        CodecConfig(channels=channels, error_correction=error_correction)
    )


def _read_text(path: Optional[str]) -> str:
    if path in (None, "-"):
        return sys.stdin.read()
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _write_text(path: Optional[str], text: str) -> None:
    if path in (None, "-"):
        sys.stdout.write(text)
    else:
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)


def _payload_from_args(args: argparse.Namespace) -> bytes:
    if args.hex is not None:
        return bytes.fromhex(args.hex)
    if args.text is not None:
        return args.text.encode("utf-8")
    raise TextSteganographyError("provide a payload with --text or --hex")


def _cmd_analyze(args: argparse.Namespace) -> int:
    codec = _build_codec(args.channels, args.ecc_repeat)
    report = codec.analyze(_read_text(args.input))
    if args.json:
        payload = {
            "codec_id": codec.codec_id,
            "total_sites": report.total_sites,
            "realizable_packed_bits": report.realizable_packed_bits,
            "usable_payload_bytes": report.usable_payload_bytes,
            "max_distinct_payloads": report.max_distinct_payloads,
            "per_channel": [
                {"channel_id": c.channel_id, "sites": c.sites, "packed_bits": c.packed_bits}
                for c in report.per_channel
            ],
        }
        print(json.dumps(payload, indent=2))
        return 0
    print(f"codec_id:                  {codec.codec_id}")
    print(f"total sites:               {report.total_sites}")
    print(f"raw theoretical bits:      {report.raw_theoretical_bits:.1f}")
    print(f"realizable packed bits:    {report.realizable_packed_bits}")
    print(f"framing overhead bits:     {report.framing_overhead_bits}")
    print(f"integrity overhead bits:   {report.integrity_overhead_bits}")
    print(f"usable payload bytes:      {report.usable_payload_bytes}")
    print(f"distinct payloads:         {report.max_distinct_payloads}")
    for channel in report.per_channel:
        print(f"  - {channel.channel_id}: {channel.sites} sites, {channel.packed_bits} bits")
    return 0


def _cmd_encode(args: argparse.Namespace) -> int:
    codec = _build_codec(args.channels, args.ecc_repeat)
    cover = _read_text(args.input)
    result = codec.encode(cover, _payload_from_args(args))
    _write_text(args.output, result.text)
    if args.output not in (None, "-"):
        print(
            f"encoded {result.payload_size} bytes into {result.sites_used}/"
            f"{result.sites_total} sites (codec {result.codec_id})",
            file=sys.stderr,
        )
    return 0


def _cmd_decode(args: argparse.Namespace) -> int:
    codec = _build_codec(args.channels, args.ecc_repeat)
    result = codec.decode(_read_text(args.input))
    if args.json:
        print(
            json.dumps(
                {
                    "status": result.status.value,
                    "codec_id": result.codec_id,
                    "payload_hex": result.payload.hex() if result.payload else None,
                    "integrity_valid": result.integrity_valid,
                    "observed_sites": result.observed_sites,
                    "known_symbols": result.known_symbols,
                    "erasures": result.erasures,
                    "corrected_errors": result.corrected_errors,
                },
                indent=2,
            )
        )
    else:
        print(f"status:          {result.status.value}")
        print(f"codec_id:        {result.codec_id}")
        if result.payload is not None:
            print(f"payload (hex):   {result.payload.hex()}")
            try:
                print(f"payload (utf-8): {result.payload.decode('utf-8')}")
            except UnicodeDecodeError:
                print("payload (utf-8): <not valid utf-8>")
        print(f"integrity:       {result.integrity_valid}")
        print(
            f"sites:           {result.observed_sites} observed, "
            f"{result.known_symbols} known, {result.erasures} erased"
        )
        print(f"corrected errors:{result.corrected_errors:>2}")
    return 0 if result.payload is not None else 1


def _cmd_inspect(args: argparse.Namespace) -> int:
    report = inspect_text(_read_text(args.input))
    if args.json:
        print(
            json.dumps(
                {
                    "length": report.length,
                    "scripts": list(report.scripts),
                    "mixed_scripts": report.mixed_scripts,
                    "nfc_differs": report.nfc_differs,
                    "nfkc_differs": report.nfkc_differs,
                    "notable": [
                        {"index": n.index, "codepoint": n.codepoint, "name": n.name, "note": n.note}
                        for n in report.notable
                    ],
                },
                indent=2,
            )
        )
        return 0
    print(report.summary())
    for note in report.notable:
        print(f"  [{note.index}] {note.codepoint} {note.name} ({note.note})")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tsteg", description="Hide and recover payloads in the entropy of text."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(sub: argparse.ArgumentParser, *, with_channels: bool = True) -> None:
        sub.add_argument("-i", "--input", default="-", help="input file, or - for stdin")
        if with_channels:
            sub.add_argument(
                "-c",
                "--channels",
                default=DEFAULT_CHANNELS,
                help="comma-separated channel ids",
            )
            sub.add_argument(
                "--ecc-repeat",
                type=int,
                default=1,
                metavar="N",
                help="repetition-code redundancy (N copies per bit; 1 disables ECC)",
            )

    analyze = subparsers.add_parser("analyze", help="report capacity for a text")
    add_common(analyze)
    analyze.add_argument("--json", action="store_true", help="emit JSON")
    analyze.set_defaults(func=_cmd_analyze)

    encode = subparsers.add_parser("encode", help="embed a payload into a cover text")
    add_common(encode)
    encode.add_argument("-o", "--output", default="-", help="output file, or - for stdout")
    payload_group = encode.add_mutually_exclusive_group(required=True)
    payload_group.add_argument("--text", help="payload as a UTF-8 string")
    payload_group.add_argument("--hex", help="payload as hex bytes")
    encode.set_defaults(func=_cmd_encode)

    decode = subparsers.add_parser("decode", help="recover a payload from stegotext")
    add_common(decode)
    decode.add_argument("--json", action="store_true", help="emit JSON")
    decode.set_defaults(func=_cmd_decode)

    inspect_cmd = subparsers.add_parser("inspect", help="report notable code points")
    add_common(inspect_cmd, with_channels=False)
    inspect_cmd.add_argument("--json", action="store_true", help="emit JSON")
    inspect_cmd.set_defaults(func=_cmd_inspect)

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except TextSteganographyError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (ValueError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
