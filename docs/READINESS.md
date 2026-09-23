# Readiness follow-up — September 23, 2026

The F1–F6 fixes were merged in [PR #16](https://github.com/cpsherrill/text-steganography/pull/16).
[CI on the merged main commit passed](https://github.com/cpsherrill/text-steganography/actions/runs/35893725214).
This follow-up covers capacity reporting, cleanup, and realistic local validation.
Release versioning, tags, and publication remain a separate decision and PR.

## Capacity output contract

Python's integer-to-string safety limit caused `tsteg analyze` to fail on larger
covers (reproduced on Python 3.11 with roughly 16,000 eligible spaces). The count
of possible payloads is a power of two and does not need thousands of digits.
The fix leaves the interpreter's protection enabled.

- Text output prints a decimal count up to `2^53 - 1`, then the exact `2^N` form.
- JSON `max_distinct_payloads` remains a number up to `2^53 - 1` and is `null`
  above that bound. This avoids rounding in consumers using IEEE-754 numbers.
- JSON adds `max_distinct_payloads_log2`: an integer N for the exact count `2^N`.
  It is `null` when no frame fits, and 0 when only an empty payload fits.
- The Python API's `CapacityReport.max_distinct_payloads` remains an exact integer.
- These counts describe payloads at the maximum usable byte length, not the sum
  of all possible lengths and not a measured number of distinguishable recipients.

Examples:

| Capacity outcome | JSON count | JSON log2 | Text count |
| --- | ---: | ---: | --- |
| No complete frame fits | 0 | null | 0 |
| Only an empty payload fits | 1 | 0 | 1 |
| One payload byte | 256 | 8 | 256 |
| 1,991 payload bytes | null | 15928 | 2^15928 |

JSON consumers must handle the nullable count and use the exponent when needed.
Tests exercise both output formats and an interpreter limited to 640 decimal
digits. No global interpreter settings are changed.

## Additional Markdown correction

Independent Markdown parsing showed that a multiline reference definition's
continuation title could be altered. The scanner now protects the entire
nonblank run starting at a reference definition. It can exclude additional prose
conservatively, but no longer treats continuation-title spaces as payload sites.

Markdown carrier version **3** freezes this changed site-discovery rule. Saved
version 2 configurations are rejected. Use version 2 of the code for previously
encoded copies, and encode new copies from original covers using a newly saved
configuration. Other carrier/channel versions and plain-text golden vectors are
unchanged by this follow-up.

## Verification

486 tests pass locally on Python 3.9.6 and 3.11. Coverage on Python 3.9.6 is
**94.16% combined**. The 90% CI floor remains in place. Independent document
checks use html5lib and markdown-it-py as development-only dependencies; the
runtime still has no dependencies. Source/wheel builds and an isolated Python 3.11
wheel install pass both CLI entry points, all three examples, and the strict-limit
large JSON report regression.

See [realistic validation](REALISTIC_VALIDATION.md) for saved samples, actual
transport scope, damage behavior, and measured performance. These checks do not
certify arbitrary markup or an untested external application.

## Next decisions, separately tracked

- [#17: named application transport measurements](https://github.com/cpsherrill/text-steganography/issues/17).
- [#18: larger-document and recipient-set scaling](https://github.com/cpsherrill/text-steganography/issues/18).
- [#19: first alpha scope and separate release PR](https://github.com/cpsherrill/text-steganography/issues/19).

Agree on the alpha's supported use cases, version, distribution destination,
and compatibility promises before making a release-only PR. No tag or package
publication is part of this readiness work.
