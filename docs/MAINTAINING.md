# Maintainer workflow

Use a focused branch and pull request. Install `.[dev]`, run `python -m pytest
--cov`, and check `git diff --check`. For packaging changes also run `python -m
build` and verify installation outside the checkout. Test-only parser packages
must not become runtime dependencies.

CI runs on pull requests, pushes to `main`, and manual dispatch. Branch pushes
are not also tested separately when a pull request is open.

## Main-branch protection

As configured on September 23, 2026, GitHub requires a pull request and these
GitHub Actions checks, including for administrators:

- Python 3.9, 3.10, 3.11, 3.12, 3.13, and 3.14 on `ubuntu-latest`.
- Python 3.13 on `macos-latest` and `windows-latest`.
- `Build and test the installed wheel`.

The branch must be current with main before merging. Force pushes and branch
deletion are disabled. A second person's approval is not required, so a solo
maintainer can merge after checks pass. Protection is GitHub repository state,
not a setting installed by cloning these files. If CI job names change, update
the required check names too; otherwise merges will wait for nonexistent checks.

## Evidence and releases

Keep measured transport records scoped to their exact route and environment.
Do not send samples to external recipients without explicit authorization.
Record newly discovered limitations as issues and keep the changelog current.
Keep essential regression fixtures, scripts, and concise result metadata in Git.
For recurring runs, place bulk dated samples in a durable external archive with
checksums and links; do not rely on expiring CI artifacts as the only record.
The small initial baseline remains committed until an archive destination is
agreed, so cleanup does not discard the evidence or force a premature release.

The first release has its own [decision issue #19](https://github.com/cpsherrill/text-steganography/issues/19).
Keep version changes, release notes, and publishing configuration in a separate
release PR after agreeing on scope. Merging ordinary fixes does not create a
release or authorize package publication.

## Decoding compatibility decision before the first release

Design section 4.9 promises that released copies stay decodable later. Current
registries retain only one implementation per component ID; a version mismatch
is rejected. That is explicit failure rather than a compatibility implementation.
The Markdown v2-to-v3 transition occurs before any published release.

The proposed policy in #19 is to preserve decoding for released format versions,
using version-specific implementations and historical golden vectors. Legacy
implementations need not remain available for new encoding. This proposal still
needs a defined support scope and implementation before claiming that guarantee;
it is not delivered by a component version bump alone. If the release instead
requires an exact library version for decoding, revise the design promise and
release documentation explicitly before publishing. Never reinterpret an old
configuration as a new layout just to bypass a version check.
