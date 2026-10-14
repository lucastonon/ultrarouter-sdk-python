# Security policy

## Reporting a vulnerability

Please report security issues privately, not in public issues or pull requests. Use GitHub's
private vulnerability reporting on this repository (**Security** tab, **Report a vulnerability**).
Include a description, the affected version, and steps to reproduce. We aim to acknowledge reports
within three business days and will keep you informed while we investigate and fix the issue.

## Supported versions

| Version | Supported |
| --- | --- |
| 0.0.x | yes (latest release) |

## How the SDK handles sensitive data

- API keys are sent only in the `Authorization` header to the configured base URL. They are never
  logged, printed or included in error messages; `repr()` of a client omits the key.
- The SDK does not log requests, responses or outcome events.
- Outcome and reviewer events carry ids, hashes and numeric values. Draft and final texts are sent
  only if you pass them explicitly (for workspaces with corrections consent); `diff_stats` lets you
  report edits without sending text.
- Reviewer events, candidate decisions and pull-oracle calls are signed with HMAC-SHA256 over the
  exact request bytes.
- Path parameters (ids, slugs) are percent-encoded so they cannot change the request route.
- `FileOutcomeStore` writes its queue file with mode `0600` and never overwrites a queue file it
  cannot read or parse (it raises `OutcomeStoreError` instead).
- Every call has a total deadline (`timeout`) that also covers reading the response body.

## How releases are checked

Releases are built and uploaded by GitHub Actions with PyPI trusted publishing (no stored token),
and every third-party action is pinned to a full commit SHA.

Every release candidate is scanned for credentials (common provider key and token formats,
private-key blocks), absolute local paths and committed secret files, across the working tree,
the complete git history and the contents of the built wheel and sdist
(`scripts/leak_scan.py`).

## Keys in your own code

Read keys from the environment or a secret manager. Use test keys (`ur_sk_test_...`) for
development, CI and Bench.
