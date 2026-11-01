# Release guide

## Overview

Releases are triggered by pushing a Git tag named `vX.Y.Z`, such as `v0.3.0`.
The release workflow builds architecture-specific wheels, creates a GitHub
release, and publishes to PyPI with OIDC trusted publishing. No PyPI API token
is stored as a repository secret.

## Prepare a release

1. Bring the release branch up to date:

   ```bash
   git checkout main
   git pull origin main
   ```

2. Confirm all planned changes are merged and CI is green.

3. Add a new section to `CHANGELOG.md` using the required header format:

   ```markdown
   ## [X.Y.Z] - YYYY-MM-DD
   ```

   The workflow extracts this section for GitHub release notes.

4. Commit the changelog update, then create and push the tag:

   ```bash
   git tag vX.Y.Z
   git push origin main vX.Y.Z
   ```

Do not reuse or move an existing public tag.

## Publish job

For each supported architecture, the workflow:

1. Initializes the appropriate EESSI environment.
2. Builds an EESSI-versioned `libvdi.so`.
3. Bundles the libraries in a platform wheel.
4. Uploads the wheel as a workflow artifact.

The publication job sends the artifacts to PyPI using GitHub OIDC. Reviewers,
if configured on the `pypi` GitHub environment, must approve publication before
it proceeds.

## Verify a published release

After publication succeeds, install the released package in a clean environment:

```bash
python -m pip install --upgrade vdi-client
vdi --version
```

Check that:

- the version matches the tag
- the expected platform wheel is visible on PyPI
- `vdi run` works with each supported EESSI version and architecture
- the GitHub release contains the expected notes and artifacts

## Manual recovery

If build jobs fail, keep the tag unchanged. Fix the issue, delete the failed Git
release object if one was created, and rerun the failed workflow jobs.

If publication fails after some files reach PyPI, do not republish identical
filenames. Resolve the issue, increment the patch version if a new distribution
is required, and release that version normally.
