# Code Signing Policy

CabreChess Windows release binaries are built and signed using free code signing
provided by [SignPath.io](https://signpath.io/) through the
[SignPath Foundation](https://signpath.org/) for open source projects.

## Provenance

- All signed binaries are built from this public repository's source code by
  [GitHub Actions](.github/workflows/release.yml), never from a local machine.
- Only builds triggered from tagged releases on the `master` branch are submitted
  for signing.
- Each release is accompanied by a SHA256 checksum (see [Releases](../../releases))
  so the signed binary can be independently verified against the build log.

## Roles

| Role      | Person                                      |
|-----------|----------------------------------------------|
| Author    | Federico Cabrera (federicocabrera1978-svg)   |
| Reviewer  | Federico Cabrera (federicocabrera1978-svg)   |
| Approver  | Federico Cabrera (federicocabrera1978-svg)   |

As a single-maintainer project, the same person currently holds all three roles.
Multi-factor authentication is enabled on the GitHub and SignPath accounts used
to manage releases.

## Privacy

CabreChess does not collect, transmit, or store any personal data. It has no
network functionality; games and settings are only ever saved locally, and only
when the user explicitly chooses to save a file via the OS file dialog.

## Acknowledgement

Certificates used to sign CabreChess releases are provided free of charge by the
[SignPath Foundation](https://signpath.org/) using
[SignPath.io](https://signpath.io/)'s code signing platform.
