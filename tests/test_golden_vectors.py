from __future__ import annotations

import json
import pathlib

import pytest

from text_steganography import CodecConfig, DecodeStatus, TextSteganographyCodec

VECTOR_DIR = pathlib.Path(__file__).parent / "vectors"
VECTORS = sorted(VECTOR_DIR.glob("*.json"))


def test_vectors_exist():
    # a guard so an empty directory does not silently pass the suite
    assert VECTORS, "no golden vectors found"


@pytest.mark.parametrize("path", VECTORS, ids=[p.name for p in VECTORS])
def test_golden_vector(path: pathlib.Path):
    data = json.loads(path.read_text(encoding="utf-8"))
    config = CodecConfig.from_dict(data["config"])
    codec = TextSteganographyCodec(config)

    # the configuration still hashes to the stored id
    assert codec.codec_id == data["codec_id"]

    payload = bytes.fromhex(data["payload_hex"])

    # encoding the cover reproduces the exact stegotext, byte for byte
    produced = codec.encode(data["cover_text"], payload).text
    assert produced == data["expected_stego"]

    # decoding the frozen stegotext recovers the payload
    decoded = codec.decode(data["expected_stego"])
    assert decoded.status is DecodeStatus.SUCCESS
    assert decoded.payload == payload
