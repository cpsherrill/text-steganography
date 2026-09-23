# Fixed-block ECC contract — September 16, 2026

F6 is addressed. The implementation and its dependency-free regression adapters
are tested in [`test_ecc_contract.py`](../tests/test_ecc_contract.py).
The bundled identity and repetition codecs retain their encoded bytes and
configuration IDs. No external ECC dependency has been added.

## The original bug

An ECC adapter maps **k message bits** to **n encoded bits** per block. The frame
header is 40 message bits. The old decoder read `40 // k` blocks, rounding down.
For k=16 it recovered only 32 header bits; a valid one-byte payload encoded but
failed to decode. Encoding also rejected incomplete final message blocks while
capacity calculations rounded their sizes up.

## Implemented rules

### Whole blocks and logical prefixes

`decode_prefix(observed, H)` reads `ceil(H / k)` complete codeword blocks and
returns exactly the first H recovered bits. Header and full-frame decoding use
this same operation. Too few encoded bits produce `insufficient`; an adapter
that cannot recover a block produces `uncorrectable`.

For k=16, the header requires three blocks. Their 48 message bits include the
40-bit header and eight more bits that may be payload. Those extra bits are
**not padding** and must not be checked as padding during header decoding.

### Padding belongs to the shared ECC layer

The logical frame is header + payload + CRC. `encode_bits` appends zero bits
until the complete frame length is a multiple of k. Padding follows the CRC
and is excluded from both the payload length and CRC input. Empty input to the
ECC helper has no blocks; an empty *payload* still has a 72-bit frame.

For k=16, an empty payload therefore uses five blocks: 72 frame bits plus eight
zero bits. Full-frame decoding uses `check_padding=True` to reject nonzero
recovered padding, then removes the padding before checking the frame and CRC.
A corrupted padding bit that ECC corrects to zero is acceptable.

Adapters implement fixed-size blocks. They must not add implicit shortening or
padding of their own. A future shortened-code convention needs separate,
explicitly versioned rules.

### Shared size calculations

For a logical frame of L bits and a carrier with C usable bits:

- Padding: `(-L) % k`.
- Encoded bits required: `ceil(L / k) * n`.
- Available whole message bits: `floor(C / n) * k`.
- Maximum payload bytes: `min(65535, floor((available - 72) / 8))`, provided
  at least the 72-bit empty frame fits.

`analyze`, `encode`, `preflight`, and candidate identification use these shared
helpers. Candidate predictions include the same zero padding as encoding.
`ecc_overhead_bits` measures redundancy plus padding for the largest fitting
frame, excluding unused carrier bits; it is zero if no frame fits. A reported
zero-byte capacity can mean that only an empty payload fits or no frame fits;
use `preflight` to distinguish them.

### Adapter authoring and validation

Implement `encode_block`, `decode_block`, and serializable `params` (plus
`from_params` if needed). Keep the shared stream, prefix, and size helpers.
Adapters must be deterministic: identical parameters and input must produce
identical output. The framework validates shapes, not an algorithm's mathematical
correction guarantees.

- Declare nonempty string `id` and `version`, and integer block sizes with
  `1 <= k <= n`. The identity ID `ecc.none` is reserved for k=n=1.
- `encode_block` accepts k binary integers and returns a list or tuple of n
  binary integers. Booleans, nonbinary values, and wrong lengths are rejected.
- `decode_block` accepts n values, each 0, 1, or `None` for an erasure. Do not
  silently convert erasures to zeros.
- Return `BlockResult(bits, corrected)`: exactly k recovered binary integers,
  or `bits=None` when uncorrectable. `corrected` counts observed positions that
  disagree with the recovered decision, excluding erasures; it must be an
  integer between zero and the number of known input positions.
- The core calls `decode_block_checked`, which validates adapter results.
  Malformed results and unexpected adapter exceptions raise `ConfigError`.
  Adapters must return an uncorrectable result for ordinary uncorrectable data.
- Frame bytes use most-significant-bit-first ordering. A byte-symbol adapter
  must explicitly map this stream to its symbols and define how partial-byte
  erasures become symbol erasures. Those choices belong in its versioned
  implementation/parameters and interoperability tests.

The core translates incomplete input into `INSUFFICIENT_EVIDENCE`, uncorrectable
blocks into `PARTIAL`, and invalid magic/version, padding, or CRC into `INVALID`.
Payload bytes are returned only after successful full-frame validation. CRC is
an integrity check, not authentication or proof of sender identity.

### Stable serialized layout

Multi-bit adapters add this field to their serialized `error_correction` entry
(example k=16, n=48):

```json
"block_layout": {
  "message_bits": 16,
  "codeword_bits": 48,
  "padding": "zero_pad_v1"
}
```

The layout, adapter ID/version, and parameters contribute to `codec_id`. Reload
rejects missing or mismatched multi-bit layouts. Existing one-bit configurations
retain their serialization and IDs. Keep versioned algorithm parameters and
symbol ordering stable as well; matching block sizes alone does not establish
wire compatibility.

## Verification and remaining scope

The suite exercises explicit k=1, 7, 8, 16, 24, and 64 and generated k up to 80;
empty/boundary payloads; exact and insufficient capacity; headers crossing block
boundaries; errors and erasures; invalid padding, frame versions, lengths, and
CRC; adapter contract violations; configuration reload; candidate predictions;
and the unchanged identity/repetition golden vectors.

These changes resolve the identified F6 integration defect and inconsistent
padding/capacity behavior. They do not prove that every future adapter or input
is correct. Before adding an external adapter, independently evaluate its coding
properties, erasure support, licensing, maintenance, and Python compatibility;
add known-answer/interoperability tests against that implementation. Interleaving,
shortened codes, and insertion/deletion recovery remain separate work.
