# Changelog

## Unreleased

### Fixed

- Resolve assessment findings F1–F6: Unicode site stability, protected carrier
  regions, configuration enforcement, evidence-aware identification, carrier-aware
  probes, and fixed-block ECC framing/padding.
- Keep API report logging/serialization and CLI capacity reports bounded. Human-readable output uses `2^N` for
  large counts; JSON includes an exact `max_distinct_payloads_log2` exponent and
  uses `null` for counts exceeding the interoperable JSON integer range.
- Run push CI only on main, retaining PR and manual runs without duplicate
  branch-push jobs.
- Protect multiline Markdown reference definitions, including continuation titles.

### Added

- Regression, property-based, independent parser, CLI, and runnable example tests.
- CI across Python 3.9–3.14, macOS and Windows, plus distribution installation checks.
- Reproducible local transport records and a core performance measurement script.
- Maintainer guidance and a documented, separate first-release decision process.

### Compatibility

- Canonical Unicode and zero-width channels, HTML and source-code carriers use
  version 2. Markdown now uses version 3 after the continuation-title fix.
  Earlier changed-component configurations are rejected; use their matching old
  code for old copies, and create new copies/configurations from original covers.
- Risky channels require explicit policy permissions. Some unstable combinations
  and unsupported source syntax are rejected before encoding.
- Probe format 2 excludes protected regions and reports unavailable rates when
  site counts cannot align.
- Multi-bit ECC configurations record block geometry and `zero_pad_v1` explicitly.
- Large CLI JSON capacity counts are now nullable; see
  [the output contract](docs/READINESS.md#capacity-output-contract).
- Existing plain-text identity/repetition golden vectors and codec IDs remain
  unchanged. The exact integer count is now a computed property; the report
  constructor and `dataclasses.asdict` schema store `max_distinct_payloads_log2`
  instead. `to_dict()` provides safe numeric counts plus the exponent.

The package remains `0.0.0`; this is not a published release. See
[hardening](docs/HARDENING.md) and [readiness](docs/READINESS.md) for details.
