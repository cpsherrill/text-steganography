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

Early scaffold. The full design is written and lives in
[docs/DESIGN.md](docs/DESIGN.md). No functionality is implemented yet. This
commit is the repository skeleton: packaging, license, and the design of
record.

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
controls, semantically active joiners) are opt-in by design, and diagnostics
report exactly which characters were introduced. The threat models and the
full list of caveats are in the design document.

## Install

Nothing is published yet. For a development checkout:

```bash
git clone git@github.com:cpsherrill/text-steganography.git
cd text-steganography
python3 -m pip install -e ".[dev]"
```

Requires Python 3.9 or newer.

## Planned phases

The design lays out a staged build. In short:

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
