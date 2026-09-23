# Example workflows

These examples exercise small, controlled fixtures. They do not certify a
particular messaging service or arbitrary document syntax. Read the
[implementation assessment](../docs/ASSESSMENT.md) before choosing a workflow.

## Setup

From the repository root, in a virtual environment:

```sh
python -m pip install -e '.[dev]'
python examples/recipient_fingerprints.py
python examples/transport_probe.py
python examples/source_comments.py
```

All three examples contain checks and are exercised by pytest and CI.

| Example | Demonstrates | Important boundary |
| --- | --- | --- |
| `recipient_fingerprints.py` | Preflight 30 tokens, encode copies, serialize the configuration, decode a copy, identify an excerpt | Exact canonical excerpt; retain the original cover, configuration, and recipient mapping. A ranked candidate is not proof. |
| `transport_probe.py` | Compare unchanged text with local NFKC normalization; derive an advisory profile | Synthetic transformation only; this does not measure email, chat, or a CMS. Uses plain text as a simple control; carrier-aware measurements now exclude protected regions. |
| `source_comments.py` | Embed in a simple Python comment, decode, compare untouched code and syntax trees | A deliberately simple fixture; the current scanners cannot guarantee safety for arbitrary source or markup. |

## File-based command-line workflow

Use a disposable UTF-8 cover file with at least 200 ordinary inter-word spaces:

```sh
tsteg analyze -i cover.txt
tsteg encode -i cover.txt -o marked.txt --text r17
tsteg decode -i marked.txt --json
tsteg inspect -i marked.txt
```

For an actual transport experiment:

```sh
tsteg probe-make -o sample.txt --save probe.json
# Send sample.txt through the exact route to be evaluated.
# Save the returned text verbatim as returned.txt.
tsteg probe-check --probe probe.json -i returned.txt --json
```

Record the date, application/version, copy/paste or attachment path, exact
configuration, and before/after samples. First test a byte-exact round trip as
a control. Measure the actual path: a file attachment and pasting into the same
application can behave differently. Do not infer successful payload recovery
from the probe alone; encode and decode representative payloads too.

Retain the original cover and exact configuration for each distribution.
Zero-width re-encoding is supported with explicit joiner permission. Unicode
normalization, retyping, or structural changes can destroy a mark. Incompatible
canonical-Unicode/channel combinations are rejected. Changed site counts return
an untested probe result with no survival percentage; unchanged counts alone
are not proof of successful payload recovery. See [the hardening notes](../docs/HARDENING.md)
for supported source syntax and configuration-version migration.

See [realistic-use validation](../docs/REALISTIC_VALIDATION.md) for recorded local
file/ZIP/pipe/pasteboard experiments and their limits. These examples remain
small demonstrations; named external applications still require their own tests.
