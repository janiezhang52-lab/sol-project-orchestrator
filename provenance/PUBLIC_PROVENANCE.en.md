# Public provenance

[简体中文](PUBLIC_PROVENANCE.md) | English

This document records public technical identity only. It excludes local paths, locations of private acceptance material, task IDs, and account information.

## Formal release identity

- Version: `0.3.3`
- Formal ZIP: `sol-project-orchestrator-0.3.3.zip`
- Formal ZIP bytes: `31633`
- Formal ZIP SHA-256: `92a62af2641e027390c8bbfe2d64d710bc2fb5f267cf470cb75d5dc31d3c0b84`
- Release tree SHA-256: `0cb9a029e29cd57af9609d4b6be88dfe63e5dd8dfc9c424afb9e90fedd5641ae`

The seven regular files in the formal ZIP match the formal [release tree](../release/sol-project-orchestrator/) byte for byte according to the release record. Private development Git object identities remain in internal frozen records and are not published here.

The [published v0.3.3 release](https://github.com/janiezhang52-lab/sol-project-orchestrator/releases/tag/v0.3.3) supplies the formal ZIP and its checksum. Documentation updates do not rebuild that ZIP or change its identity.

## Public repository history

The public repository has its own history, separate from the private development history. The published `v0.3.3` tag identifies the public release snapshot. See the tag in the repository for its public commit identity; it must not be represented as private development history.

[source-manifest.json](source-manifest.json) and the root [SHA256SUMS.txt](../SHA256SUMS.txt) are retained frozen-snapshot records. Their pre-publication status fields and file hashes describe that recorded snapshot, not every later README edit or translation. They are not a current-branch completeness claim. This documentation update leaves those records and the seven runtime release files untouched; Git records the new documentation files and revisions.

## Platform validation boundary

The same exact formal ZIP completed the full product chain in fresh Windows Git and fresh macOS Git projects. Each reached `PRODUCT_ACCEPTED` only after the user's explicit final product decision. These results apply to that exact ZIP and cannot be extrapolated to later modifications or repackaged artifacts.

## Static-suite boundary

The v0.3.3 frozen source passed the original full suite, `59/59`, in the formal product repository. This public snapshot excludes private `CURRENT/GAPS` state documents. Its public-layout suite recorded `57/57 PASS`; the two omitted checks concern only those private state documents, not runtime code.

The source manifest records per-file source classification, size, and SHA-256 for the frozen snapshot. For checks performed during the English documentation update, see the [documentation coverage and validation record](../docs/DOCUMENTATION-COVERAGE.md).
