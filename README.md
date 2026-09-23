# text-steganography

> Hide small payloads in the entropy of a text's literal representation,
> without changing what a reader sees.

A modular Python library for lossless text steganography and fingerprinting.
It embeds hidden data into text by choosing between representations that look
the same to a person but differ in the underlying characters: one apostrophe
code point rather than another, one Unicode space rather than another, one
canonical-equivalent Unicode sequence rather than another, a zero-width mark
at an eligible spot, and so on. The reader sees the same words. The bytes are
different, and the difference carries the payload.

## Status

**Unreleased alpha (`0.0.0`), hardened September 23, 2026.** The core workflow
and substantial portions of phases 2–4 are implemented. Assessment findings
F1–F6 are addressed, including generic ECC block/framing integration.
See [the hardening notes](docs/HARDENING.md) for fixes, explicit supported
boundaries, and configuration migration, and [the ECC contract](docs/ECC_ADAPTER_CONTRACT.md)
for the implemented block and padding rules.

See the [implementation assessment](docs/ASSESSMENT.md) for architecture,
measured coverage, and reproducible defects, and [example workflows](examples/README.md)
for runnable demonstrations. Implemented today:

- the `analyze` / `encode` / `decode` / `canonicalize` workflow;
- five channels: Unicode spaces, contraction apostrophes, cross-script
  homoglyphs, zero-width joiners, and canonical-Unicode composition (the last
  two change length, so excerpt alignment is refused while they are enabled);
- versioned configuration with a stable `codec_id`;
- power-of-two packing and `length_crc_v1` framing with integrity checks;
- a pluggable error-correction layer, with a repetition code that corrects
  bit flips and erasures (the default is still no ECC);
- candidate identification: trace a leaked copy to one of N known payloads,
  with a fingerprint preflight (`encode_many`, `preflight`, `identify`);
- fragment alignment: trace a leaked excerpt by locating it in the original
  cover, so only the sites it covers have to survive;
- a transport probe that measures which channels actually survive a real
  send-and-return path and labels each Recommended / Conditional / Fragile /
  Unsupported (or Untested when site counts no longer align); protected
  carrier regions are excluded from the measurement;
- compatibility profiles: advisory per-channel recommendations for a
  carrier/transport, either chosen from built-ins or built from a probe
  measurement (recommendations only; the configuration stays yours);
- carrier adapters for plain text, HTML, Markdown, and source code with protected
  region tests, HTML parsing, and Python tokenization; unsupported source syntax
  fails explicitly (see the hardening notes for the supported subset);
- the `inspect` diagnostic and a `tsteg` command-line tool;
- golden vectors, property-based tests, and runnable workflow tests;
- GitHub Actions configuration for tests, coverage, and distribution checks
  ([merged-main CI passed](https://github.com/cpsherrill/text-steganography/actions/runs/35893725214)).

Locally verified on Python 3.9 and 3.11: **486 passing tests, no expected failures**.
Python 3.9 combined statement/branch coverage is **94.16%**. Tests include fixed-block ECC boundaries and damaged input, every
canonical Unicode decomposition pair in the local runtime, generated Unicode
covers, compatible channel combinations, and protected document regions.
Passing tests do not establish safety for arbitrary document extensions or
real-world transport paths.

Not built yet: sequence alignment for excerpts altered by insertion or deletion,
mixed-radix packing, keyed placement, and collusion-resistant fingerprint codes.
The full plan and the reasoning behind it live in [docs/DESIGN.md](docs/DESIGN.md).

See [the changelog](CHANGELOG.md), [readiness follow-up](docs/READINESS.md),
and [realistic-use measurements](docs/REALISTIC_VALIDATION.md). Large CLI JSON
capacity counts are nullable and have an exact exponent; Markdown carrier 3
protects multiline reference definitions.

## The core idea

You start with ordinary **cover text** and a small **payload**. A versioned
**codec configuration** names the **channels** to use (punctuation variants,
Unicode-space variants, canonical-equivalent sequences, and more), each of
which finds its own eligible sites and offers a set of visually equivalent
variants. The encoder writes the payload into those choices and returns
**stegotext**. The decoder, given the same configuration, rediscovers the
sites and reads the payload back out. No separate placement manifest is
needed for intact text.

A central use case is **recipient fingerprinting**: give one document to a
thousand recipients, each a visually equivalent but literally distinct copy,
so that a leaked copy can be traced. When only part of a copy survives, or
some channels have been normalized away, the library aims to narrow the
source to the candidates still consistent with the surviving evidence rather
than failing outright.

Capacity analysis, diagnostics, partial recovery, and honest uncertainty are
meant to be first-class, not afterthoughts.

## What this is not

- **Not encryption.** Steganography hides that a payload is present or which
  copy this is. It does not keep the payload secret. Confidentiality and
  authentication can be layered on top of the payload, separately.
- **Not a linguistic or statistical watermark.** No paraphrasing, no word
  choice, no token-probability tricks. The hiding is deterministic and
  representational.
- **Not a promise of survival.** No literal-character watermark survives
  retyping, OCR, translation, or aggressive normalization. The library states
  its assumptions and measures survival instead of promising universality.

## Safety

Some channels can break exact search, copy and paste, sorting, screen-reader
behavior, source-code identifiers, or markup, and some trip security filters
for mixed-script text. Risky channels (cross-script homoglyphs, bidirectional
controls, semantically active joiners) require explicit policy permission.
Use `RepertoirePolicy(allow_cross_script=True)` for homoglyphs or
`RepertoirePolicy(allow_joiners=True)` for zero-width insertion; CLI equivalents
are `--allow-cross-script` and `--allow-joiners`. Warnings are returned by the API
and shown by the CLI. The `scripts` field describes expected scripts; it does
not validate the Unicode Script property of the cover text.

Canonical-Unicode encoding cannot be combined with apostrophes, homoglyphs, or
zero-width insertion because those combinations do not preserve discovery.
`inspect` reports notable code points. Read [the hardening notes](docs/HARDENING.md)
before working with structured documents or saved older configurations.

## Install

Nothing is published yet. For a development checkout:

```bash
git clone git@github.com:cpsherrill/text-steganography.git
cd text-steganography
python3 -m pip install -e ".[dev]"
```

Requires Python 3.9 or newer.

## Quickstart

### Python

```python
from text_steganography import (
    ApostropheChannel,
    CodecConfig,
    TextSteganographyCodec,
    UnicodeSpaceChannel,
)

codec = TextSteganographyCodec(
    CodecConfig(channels=[UnicodeSpaceChannel(), ApostropheChannel()])
)

cover = " ".join(["it's"] * 100)

report = codec.analyze(cover)
print(report.usable_payload_bytes, "usable bytes")

stego = codec.encode(cover, b"recipient-0847").text
result = codec.decode(stego)
print(result.status.value, result.payload)   # success b'recipient-0847'

assert codec.canonicalize(stego) == cover     # invisible: it canonicalizes back
```

### Fingerprinting

```python
from text_steganography import (
    CodecConfig, TextSteganographyCodec, UnicodeSpaceChannel, RepetitionCode,
)

codec = TextSteganographyCodec(CodecConfig(
    channels=[UnicodeSpaceChannel()],
    error_correction=RepetitionCode(repeat=3),
))
cover = " ".join(["word"] * 400)
recipients = [bytes([n]) for n in range(40)]

# check the whole set fits and stays distinguishable, then hand out copies
assert codec.preflight(cover, recipients).ok
copies = codec.encode_many(cover, recipients)

# a copy turns up somewhere; trace it back
leak = copies[23].text
result = codec.identify(leak, recipients)
print(result.unique, result.best().payload)   # True b'\x17'  (recipient 23)
```

Identification works on a full-length copy whose sites may have been normalized
or flipped, and can still narrow the source even when a full `decode` fails. To
trace a shorter excerpt, pass the original cover so it can be located first:

```python
excerpt = leak[40:700]                                   # a fragment of the copy
result = codec.identify(excerpt, recipients, cover_text=cover)
```

That handles an excerpt that appears verbatim (after canonicalization) in the
cover. An excerpt altered by insertion, deletion, or retyping needs sequence
alignment, which is a later phase.

### Command line

```bash
# how much can this text carry?
tsteg analyze -i cover.txt

# embed a payload (defaults to the Unicode-space channel)
tsteg encode -i cover.txt -o stego.txt --text "recipient-0847"

# recover it
tsteg decode -i stego.txt

# see which unusual code points a text contains
tsteg inspect -i stego.txt

# measure what a real transport preserves: make a sample, send it through
# the transport (email, chat, a CMS), then check what came back
tsteg probe-make -o sample.txt --save probe.json
# ... paste sample.txt through the transport, save the result as returned.txt ...
tsteg probe-check --probe probe.json -i returned.txt

# fingerprint source code in its comments only, leaving behavior untouched
tsteg encode --carrier carrier.source_code --carrier-lang python \
  -i app.py -o app.marked.py --text "recipient-0847"
```

## Development and testing

```sh
python -m pip install -e '.[dev]'
python -m pytest --cov --cov-report=term-missing
python -m build
```

The full-suite coverage gate is 90% combined statement/branch coverage.
All six assessment findings have passing regression tests.
The [workflow](.github/workflows/tests.yml) also exercises examples and verifies
an installed wheel outside the checkout. See the [assessment](docs/ASSESSMENT.md)
for what these checks do and do not establish.

## Planned phases

The design is a roadmap, not a completion checklist. The core is implemented;
phases 2–4 have usable subsets, with explicit limitations documented in the hardening notes.
Interleaving, mature external ECC adapters, chunked fingerprints, and extensive
measured transport profiles remain outstanding alongside phase 5. In short:

1. **Unicode-string core:** versioned config, channel protocol, deterministic
   site planning, capacity analysis, power-of-two packing, framed byte
   payloads with integrity checks, encode and decode, a handful of
   conservative channels, and strong tests.
2. **Error correction and identification:** a pluggable ECC adapter, erasure
   aware observations, interleaving, and candidate filtering over a known
   payload set.
3. **Fragment alignment and profiles:** cover-text alignment, local site
   anchors, chunked fingerprints, a transport probe, and empirical
   carrier/transport profiles.
4. **Carrier adapters:** parser-aware Markdown, HTML, and selected source
   languages.
5. **Advanced capacity and tracing:** mixed-radix packing, synchronization
   aware codes, keyed placement, and collusion-resistant fingerprint codes.

See [docs/DESIGN.md](docs/DESIGN.md) for the reasoning behind every part of
this.

## License

MIT. See [LICENSE](LICENSE).
