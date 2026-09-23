# Realistic-use validation — September 23, 2026

## Document checks

The committed HTML report, Markdown report, and Python module are synthetic
fixtures shaped like ordinary project documents. Their tests go beyond our
scanner's own output:

- [html5lib](https://html5lib.readthedocs.io/en/latest/) parses HTML before and
  after embedding; tags, attributes, tree structure, and script/style content
  must remain unchanged. Only configured NBSP substitutions in prose text are
  normalized for comparison. This does not assert identical line wrapping.
- [markdown-it-py](https://markdown-it-py.readthedocs.io/en/latest/using.html)
  parses CommonMark. Token structure, links/titles, code content, and fence
  information must remain unchanged; prose spaces may use NBSP. Raw HTML blocks
  are compared as independently parsed HTML trees.
- Python's AST must remain identical, including literal strings and docstrings.
  Malformed source must fail before output is returned.

Both ordinary payloads and all-marked probes exercise the fixtures. The latter
reaches sites beyond a short payload's header/body. Additional cases cover
nested lists/quotes/fences, multiline references, hard breaks, entities, unfinished
HTML, and source tokenization failures. A multiline reference-title defect found
by these checks is fixed and versioned as Markdown carrier 3.

These are selected cases, not full CommonMark conformance or a security audit.
JavaScript regexp/template syntax, custom grammars, and arbitrary extensions
remain outside the supported subset.

## Actual local transport measurements

[Saved result metadata](validation/2026-09-23-local/results.json) includes date,
OS/Python version, base commit and dirty-tree flag, exact codec ID, and hashes.
The same directory retains cover/configuration, probe, sent and returned samples,
and ZIP archives. The experiment ran on the readiness working tree based on
`c7e4cd8`, before this follow-up was committed.

Configuration: plain-text Unicode spaces + contraction apostrophes, default
identity ECC, payload `recipient-17`, with three candidate recipients. Cover
content is synthetic; no user documents or clipboard contents are retained.

| Measured route | Byte identical | Payload recovered | Correct unique candidate | Probe survival |
| --- | --- | --- | --- | --- |
| Local UTF-8 file copy | Yes | Yes | Yes | 100% |
| ZIP compression/extraction | Yes | Yes | Yes | 100% |
| Python subprocess binary pipe | Yes | Yes | Yes | 100% |
| macOS AppKit plaintext pasteboard | Yes | Yes | Yes | 100% |

The pasteboard measurement writes and reads the OS plaintext representation. It
**does not** paste into an editor/browser or use rich-text conversion. The helper
snapshots all available clipboard formats in memory and restores them unless
another writer changes the clipboard during the test. External email, chat,
remote attachments, and publishing applications were not measured; see
[issue #17](https://github.com/cpsherrill/text-steganography/issues/17).

Reproduce portable routes in a new output directory:

```sh
python scripts/validate_local_transports.py /tmp/tsteg-new-run
```

For the optional macOS plaintext pasteboard route:

```sh
xcrun swiftc scripts/clipboard_roundtrip.swift -o /tmp/tsteg-clipboard
python scripts/validate_local_transports.py /tmp/tsteg-new-clipboard-run \
  --clipboard-helper /tmp/tsteg-clipboard
```

The recorder refuses to overwrite previous evidence. Portable routes run in CI;
clipboard testing is opt-in and is not run on hosted CI.

## Damage and scale boundaries

Automated tests separately show:

- LF/CRLF changes preserve the selected plain-text payload and candidate match.
- NFKC normalization destroys the space-channel mark even with repetition ECC
  and unchanged site counts; payload decoding fails and attribution is not unique.
- Repetition-3 corrects one changed copy of a payload bit; changing two copies
  makes CRC reject the recovered frame. These are synthetic damage tests, not
  measurements of an application transport.
- Generated arbitrary unmarked Unicode returns structured decode outcomes.

[Recorded performance](validation/benchmark-2026-09-23.json) is one run per size
on macOS arm64/Python 3.9.6, using the space channel and near-capacity all-one
payloads. All measured round trips and probes also pass correctness checks.

| Sites | Cover characters | Payload bytes | Analyze | Encode | Decode | Build probe |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2,000 | 10,004 | 241 | 0.005 s | 0.012 s | 0.008 s | 0.010 s |
| 16,000 | 80,004 | 1,991 | 0.039 s | 0.162 s | 0.061 s | 0.144 s |
| 64,000 | 320,004 | 7,991 | 0.165 s | 1.311 s | 0.250 s | 1.341 s |

Run `python scripts/benchmark_core.py` to repeat. These are observations, not
latency guarantees or CI timing thresholds. Repeated string slicing can scale
poorly; maximum-frame, multi-channel, peak-memory, and large candidate-set
measurements remain in [issue #18](https://github.com/cpsherrill/text-steganography/issues/18).
