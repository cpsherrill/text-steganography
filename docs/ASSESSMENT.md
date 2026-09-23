# Implementation assessment — September 15, 2026

> **Follow-up (September 16):** F1–F6 have been addressed in the working tree. Read
> [the hardening notes](HARDENING.md) for current behavior and verification.
> [The ECC contract](ECC_ADAPTER_CONTRACT.md) records the F6 fix. This assessment is
> retained as a historical baseline, not a list of still-unfixed problems.

## Verdict

The project is a useful alpha with a sensible decomposition and substantial
unit-test coverage. It is **not ready for dependable attribution or arbitrary
structured-document embedding**. The main weakness is insufficiently enforced
contracts between layers, rather than a need to replace the entire architecture.

Review baseline: `b513de6` (August 20, 2026). Assessment changes add documentation,
CI, examples, and tests; they do not fix the runtime defects listed below.
The earlier description of the project as a tested prototype was accurate, but
165 passing tests did not establish correctness of all advertised capabilities.

## Evidence and test coverage

Measured locally on Python 3.9.6 with branch coverage enabled:

| Metric | Existing suite | After this assessment |
| --- | ---: | ---: |
| Passing tests | 165 | 174 |
| Statement coverage | 92.50% (1615/1746) | 93.70% (1636/1746) |
| Branch coverage | 82.39% (351/426) | 83.33% (355/426) |
| Combined coverage reported by coverage.py | 90.52% | 91.67% |
| Confirmed defect cases, separately tracked | 0 | 13 strict expected failures |

The 13 defect tests are excluded from the coverage measurement. Their failures
are not counted as supported behavior. They assert desired behavior and use
strict `xfail`: a fix produces an unexpected pass that fails CI until its marker
is removed. Running with `--runxfail` displays the actual failures.

Validation also passed in an isolated Python 3.11 environment: 174 passing tests
and the same 13 expected failures. An sdist and wheel were built; the wheel was
installed into a separate environment and both CLI entry points plus all three
examples ran outside the repository. Workflow YAML and action pins were checked
locally. The full hosted operating-system/Python matrix has not yet run.

Existing strengths: capacity limits, intact round trips, stable golden vectors,
configuration serialization, CRC failures, repetition-code bit-flip recovery,
known-candidate matching, and basic carrier fixtures. Four existing
property-based tests cover bit conversion, framing, and round trips with random
payloads; they do not generate arbitrary Unicode cover text or document syntax.

Coverage is not a correctness score. Configuration has 100% combined coverage
while important configuration values are not enforced. The canonical-Unicode
channel has about 97% coverage but fails on Hangul. Missing tests primarily
concern *inputs and interactions*, not unexecuted lines.

Some baseline combined module coverage figures:

- CLI: 70.94% (now 83.25% after adding file/pipe, probe, and error-path tests).
- HTML scanner: 81.40%; Markdown: 84.67%; source code: 84.71%.
- Codec: 91.35%; probe harness: 95.65%.

## Confirmed findings

F1–F5 now have ordinary regression tests in
[`tests/test_assessment_regressions.py`](../tests/test_assessment_regressions.py).
F6 now has ordinary regression and contract tests in
[`tests/test_ecc_contract.py`](../tests/test_ecc_contract.py).
The following descriptions record the original failures.
P1 findings should block broader reliability claims; P2 is an extension-contract
problem that does not affect the two bundled ECC implementations.

### F1 — P1: Site discovery is not stable for all supported Unicode and compositions

Locations: `channels/unicode_normalization.py`, `channels/invisible/zero_width.py`,
`channels/punctuation.py`, and `core/planner.py`.

Three reproductions:

1. Encode `b"hi"` into `"가 " * 150` with the canonical-Unicode channel. Decoding
   fails. Hangul decomposes into Jamo with combining class zero, while the
   decomposed-form scanner expects nonzero combining marks. Encoded sites vanish.
2. Combine canonical Unicode and apostrophes on `"é'a " * 100`. Decomposition
   makes a combining mark the apostrophe's left neighbor; the apostrophe scanner
   no longer sees a letter. The original 200 sites become 159 in the tested copy,
   and decoding the payload fails without any transport damage.
3. Encode a zero-width payload, then encode a different payload into that output.
   Discovery skips existing marked boundaries while observation still reads
   them. Decoding the replacement payload fails.

Nonoverlapping edit spans do not guarantee independent site discovery. The
planner needs a compatibility contract and either stable canonical site
identities or explicit rejection of unsupported combinations/inputs. Unsupported
Unicode must be rejected before reporting capacity, not accepted and corrupted.

### F2 — P1: Carrier scanners can authorize edits to protected content

Locations: `carriers/html.py:safe_spans`,
`carriers/markdown.py:_inline_unsafe`, `carriers/source_code.py:safe_spans`.

- HTML: `<div title="> ...">` ends the scanner's tag at a quoted `>`.
  The remaining attribute content is treated as prose and can be changed.
- Markdown: `&copy;` is not protected from the homoglyph channel. Encoding can
  turn valid entities into unrecognized sequences, changing rendered content.
- JavaScript: `const re = /[//]/; const text = "...";` contains no comments.
  The scanner mistakes regexp slashes for a comment and permits changes to the
  string literal. A direct encode reproduces a changed string value.

These are valid input forms, not merely malformed documents. Current claims
that the scanners "never corrupt" structure or behavior are too strong.
Use parsers/tokenizers with specified syntax support or restrict adapters to a
validated subset and reject uncertain input. Test semantic preservation against
independent parsers; checking the implementation's own safe spans is insufficient.

### F3 — P1: Configuration and diagnostic promises are not enforced

Locations: `config.py`, `codec.py:__init__`, `core/planner.py:build_plan`.

- `RepertoirePolicy(allow_cross_script=False)` does not stop the homoglyph
  channel from emitting Cyrillic. The policy is serialized but not consulted.
  Documentation is inconsistent: policy says permission is required, while the
  channel says selecting it is sufficient opt-in. Choose and enforce one rule.
- A schema version of `999` or an unknown framing format is accepted; encoding
  still uses the one hard-coded frame. A configuration hash therefore describes
  requested settings that may not reflect actual behavior.
- Channel metadata contains warnings, but `plan.warnings` is never populated.
  Analysis and encoding return empty warnings even for high-risk channels.

Validate configurations centrally and reject unsupported declarations. Propagate
metadata warnings to public results and the CLI. Avoid mutable configuration
changing behavior underneath a codec after construction.

### F4 — P1: A unique candidate can be reported without any observed evidence

Locations: `codec.py:identify`, `identify/models.py:IdentificationResult.unique`.

With one candidate, an unrelated excerpt, and a cover with enough capacity,
`identify` returns `known_bits == 0` and `unique == True`. Failed alignment is
converted into an all-erasure vector; one candidate remains vacuously consistent.

Counting consistent candidates is mathematically coherent, but it must not be
presented as evidence of provenance. Preserve alignment status in identification
results and distinguish "one candidate supplied" from evidence-supported
identification. Likewise, `best()` is a ranking result even when all candidates
contradict the observation; it is not itself an attribution verdict.

### F5 — P1: Carrier-aware probes count untouched, ineligible text

Location: `probe/harness.py:build_probe` and `Probe.evaluate`.

Probe embedding uses carrier safe spans, but expected/observed symbols scan the
whole document. For an HTML attribute containing 100 unmodified spaces and a
body containing three marked spaces, removing **every embedded mark** still
reports about **97% survival**. The attribute spaces dominate the denominator.

Build expected and returned observations using the same carrier-aware mapping
as the codec. A diagnostic that measures the wrong sites must not generate
recommendations. More generally, all-identical probe symbols and ordinal
comparison do not prove alignment or payload recoverability after edits.

### F6 — P2: Generic ECC blocks are incompatible with header decoding

Locations: `ecc/protocol.py` and `codec.py:decode_message_prefix`.

The protocol permits arbitrary message block sizes, but prefix decoding uses
floor division. A valid identity adapter with 16-bit blocks encodes an 80-bit
frame, then the decoder truncates the 40-bit header to 32 bits and raises a
`FramingError` instead of recovering its one-byte payload.

Read enough whole blocks with ceiling division and trim the decoded prefix;
define padding and capacity behavior consistently. Alternatively validate a
narrower supported block-size contract. Test a block size that does not divide
the header. Bundled identity and repetition codecs use one-bit blocks, which
explains why their tests miss this.

## Architecture: what to retain and what to change

Retain these boundaries:

- Payload bytes → framing/integrity → ECC → bit packing → channel sites.
- Separate carrier adapters deciding where edits may occur.
- Separate identification and decoding: damaged evidence can rank candidates
  without recovering the complete payload.
- Explicit serialized configuration, stable golden vectors, structured results,
  and advisory compatibility profiles.
- Minimal runtime dependencies; heavyweight format parsers can be optional.

Tighten contracts before adding features:

1. **One site/observation model:** planning, decoding, probes, and excerpt
   alignment currently rediscover/filter sites separately. Define reusable
   carrier-filtered site identity and boundary rules so they cannot disagree.
2. **Validated composition:** document and check how one channel's edits affect
   every other channel's eligible sites. Span-overlap detection alone is weaker
   than the round-trip guarantee.
3. **Trustworthy results:** retain alignment failure, insufficient evidence,
   unsupported configuration, and channel warnings through the public API.
4. **Format semantics:** replace scanner safety claims with tested grammar
   support and explicit rejection where appropriate.
5. **ECC contract:** align frame, header, block size, padding, and capacity rules.

Also review scale before targeting thousands of copies: preflight computes
pairwise distances over full-capacity padded vectors, and encoding repeatedly
slices/copies strings for edits. These are complexity concerns from inspection,
not measured performance findings. No load benchmark or independent security
audit was performed.

## Recommended order of work

1. Fix F1–F5 and turn their expected failures into ordinary regression tests.
   Prioritize document corruption and unsupported combinations before broader use.
2. Resolve F6 before adding external ECC adapters.
3. Add generated Unicode cover tests, pairwise channel matrices, grammar-based
   carrier cases, and integration tests that independently check rendered or
   program semantics. Add explicit erasure/synchronization scenarios: recognizing
   a normalized zero is not the same as observing a known erasure.
4. Measure a few actual transport paths with both probes and real payloads;
   retain reproducible before/after fixtures and evidence labels.
5. Prepare a versioned alpha release after the documented contracts hold.

Advanced packing, keyed placement, interleaving/chunked fingerprints, and
collusion resistance remain roadmap work, not prerequisites for diagnosing the
current bugs. No major rewrite is needed to start addressing the findings.

## Run the current regression suite

```sh
python -m pip install -e '.[dev]'
python -m pytest --cov --cov-report=term-missing
python -m build
```

The new CI workflow configures Python 3.9–3.14 on Linux, additional macOS/Windows
jobs on 3.13, example execution, a 90% combined coverage floor, and a build/install
check outside the source checkout. The former expected failures now pass. It is
configuration, not evidence of a successful hosted run until pushed and run.
