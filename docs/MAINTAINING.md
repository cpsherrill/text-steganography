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

## Decoding compatibility policy

Decided in #19: decoding is guaranteed only with the library version that encoded
a copy (design section 4.9). Saved configurations record that version as
`created_with`, outside the `codec_id` hash, so users know which version to
install. The single source of the version is `text_steganography/_version.py`;
keep it equal to `pyproject.toml`, which a test enforces.

When changing a component's site layout or rules, bump its component version so
mismatched configurations are refused with the version hint. Do not add legacy
implementations to preserve old layouts, and never reinterpret an old
configuration as a new layout. Release notes must say which component versions
changed so users know a new library version cannot read older copies.
