# F1–F6 implementation follow-up — September 16, 2026

All six findings from [the assessment](ASSESSMENT.md) are addressed in
[PR #16](https://github.com/cpsherrill/text-steganography/pull/16), merged into main. The first five findings have 12 ordinary regression tests in
[`test_assessment_regressions.py`](../tests/test_assessment_regressions.py).
F6 has passing [block-contract tests](../tests/test_ecc_contract.py); see the
[implemented ECC contract](ECC_ADAPTER_CONTRACT.md).

## What changed

| Finding | Resolution | Deliberate boundary |
| --- | --- | --- |
| F1: unstable Unicode/sites | Canonical scanner recognizes composed and decomposed normalization units, including Hangul. Zero-width discovery/observation share one scanner and re-encoding replaces old marks. Edit ordering handles substitutions at insertion boundaries. Encoder and probe verify that observed output matches the planned stream. | Canonical Unicode may combine with Unicode spaces, but is explicitly rejected with apostrophes, homoglyphs, or zero-width insertion. Excerpt alignment still requires length-preserving channels. |
| F2: document corruption | Quote-aware HTML parsing protects attributes, entities, comments, and script/style content. Markdown protects HTML/entities, reference labels, balanced link destinations, and code delimiters. Python comments use `tokenize`, preserving strings and encoding/shebang directives. Canonicalization also respects protected spans. | Markdown is a conservative subset, not a full CommonMark/extension renderer. The lightweight JS scanner rejects regexp/division and template literals. C/custom scanners reject line splicing; custom triple-quote syntaxes require a tokenizer. These errors occur before any output is written. |
| F3: unenforced settings | Validate schema, framing, packing, duplicate/empty channels, boolean permissions, and known incompatible channels. Risky channels require explicit policy flags. Metadata warnings reach result objects and CLI output. Codecs retain a defensive configuration snapshot. | `scripts` is explicitly descriptive metadata, not a Unicode Script-property filter. Changing a codec requires constructing a new instance. |
| F4: attribution without evidence | `unique` requires known evidence. `best()` returns `None` without evidence. Identification retains the full alignment result and exposes statuses for failed/ambiguous/unsupported alignment, insufficient evidence, contradiction, and unique/ambiguous candidate matches. | A best candidate can still be contradictory; a unique consistent candidate is not a calibrated probability or proof of provenance. |
| F5: misleading probe results | Planning, decoding, and probes share whole-span carrier filtering. Protected attribute/code text no longer contributes to probe survival. Restored expectations are checked/rebuilt through the same filter. | A changed site count makes the affected channel untested and survival rates unavailable (`None`/JSON `null`). Same-count edits can still disrupt ordinal alignment; always test payload recovery too. |

## F6: fixed-block ECC framing

Header and frame decoding now read whole ECC blocks before trimming to the
logical length. The shared ECC layer appends zero padding after the complete
frame and validates it during full-frame decoding. Capacity, encoding, preflight,
and candidate identification share the same size and encoding rules. Adapter
shapes, bit values, block sizes, and correction counts are checked; adapter bugs
raise `ConfigError`, while damaged input returns structured decode statuses.
Unknown frame versions are rejected and capacity respects the 65,535-byte limit.
Empty payloads now serialize as an empty hex string in CLI JSON.

## Compatibility and migration

This remains an unreleased alpha, but changes to discovery are versioned:

- Canonical-Unicode and zero-width channels: version **2**.
- HTML and source-code carriers: version **2**. Markdown was version **2**
  in this fix; the [readiness follow-up](READINESS.md) advances it to **3**.
- Space/apostrophe mappings and the existing plain-text golden vectors remain
  unchanged. Payload framing and the bundled ECC algorithms remain unchanged.
- Multi-bit ECC configurations now record an explicit `block_layout`, including
  block sizes and `zero_pad_v1`. Missing or mismatched layouts are rejected on
  reload. Existing identity/repetition configurations and encoded bytes are
  unchanged. `ecc_overhead_bits` now measures redundancy plus padding for the
  largest fitting frame, excluding unused carrier bits.
- Stored configurations naming version 1 of a changed component are rejected.
  Do not edit their version fields to decode old copies: use the earlier code
  for those copies and generate new copies from original covers with a new
  configuration. Retain configurations with each distribution.
- Probe serialization now includes `probe_version: 2`. Legacy expectations can
  be recomputed only when their saved codec configuration is still supported;
  incompatible carrier/channel versions are not silently migrated.
- `ProbeReport.overall_survival` and per-channel rates can be `None` if alignment
  cannot be established from the site counts.

Risky-channel examples now require explicit flags:

```python
from text_steganography import CodecConfig, RepertoirePolicy, ZeroWidthChannel

config = CodecConfig(
    channels=[ZeroWidthChannel()],
    repertoire=RepertoirePolicy(allow_joiners=True),
)
```

For homoglyphs use `allow_cross_script=True`. CLI equivalents are
`--allow-joiners` and `--allow-cross-script`; these must also be provided when
reconstructing a risky codec for decoding. The saved probe already includes its
configuration.

## Verification at the F1–F6 merge

- All **453 tests pass** on Python 3.9.6 and 3.11, with no expected failures.
  Python 3.9.6 coverage is **94.50% statements**, **88.48% branches**, and
  **93.20% combined**. All regression tests contribute to coverage.
- Dependency-free ECC test adapters exercise k=1, 7, 8, 16, 24, and 64, plus
  generated sizes through k=80; empty and boundary payloads; capacity shortfalls;
  errors and erasures; invalid padding, headers, and adapter results; saved
  configuration reload; and candidate matching.
- Source distribution and wheel builds succeed. The installed wheel and examples
  are checked outside the source checkout.
- The Unicode scanner is checked against every canonically decomposable code
  point in the runtime database: 12,113 pairs on Python 3.9.6.
- Generated Unicode covers exercise combining marks, Hangul, normalization, and
  re-encoding; all 64 orderings/subsets of the four mutually compatible channels
  exercise encode/decode/re-encode and probes.
- Independent Python syntax-tree comparisons check the source-code fixture.
  Carrier tests verify protected regions remain byte-identical.
- Tests cover explicit configuration rejection, immutable codec snapshots,
  observation drift, failed alignment, saved probe migration, and changed counts.
- Existing golden vectors pass without modification.

[Hosted CI passed on merged main](https://github.com/cpsherrill/text-steganography/actions/runs/35893725214). No external ECC
adapter, new transport integration, or advanced fingerprinting feature was added.

See [the readiness follow-up](READINESS.md) for current test counts and the
subsequent capacity-reporting and Markdown fixes.
