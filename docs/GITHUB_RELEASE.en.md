# Publishing to GitHub

[简体中文](GITHUB_RELEASE.md) | **English**

## Prepare a clean source directory

From the project root, run:

```sh
python scripts/prepare_release.py
```

The script creates `release/together-workspace-v0.1.0/` and a matching ZIP from an explicit allowlist. It does not overwrite existing output; subsequent runs append a timestamp. The bundle includes source, Chinese/English documentation, launchers, deployment configuration, tests, the MIT license and a SHA-256 file manifest.

It excludes `data/`, databases, backups, sessions, user uploads, `.env`, local path configuration, caches, unused frontend prototypes and parent-repository Git history. Running the server from a release directory creates a new `data/` there, so verify that runtime data is not staged before publishing.

## Create a repository

A suggested repository name is `together-workspace`, with this description:

> A simple self-hosted team workspace with group chat, direct messages, shared files, group attachments and history search.

When initializing from a prepared release directory, create an empty repository: README, LICENSE and `.gitignore` are already included. The maintainer chooses repository visibility.

Publish **the generated directory's files** with Git or GitHub Desktop. Do not upload an entire larger parent project. If using the web uploader, include hidden `.github/`, `.gitignore` and `.dockerignore` entries. Do not publish only a ZIP: the repository should contain browsable source and a README.

The default README is Chinese; readers choose **English** at the top to open `README.en.md`. Each translated document links back to its Chinese counterpart. Both languages use the same code and data model.

After creating the repository, connect its remote and review the staged files. Before publishing, confirm:

- No `data/`, databases, backups, sessions, passwords or private files are included.
- README, LICENSE and launchers are at the repository root.
- `python -m unittest discover -s tests -v` and JavaScript syntax checks pass.
- Both documentation languages and their relative links are included in the release manifest.
- Docker and platform-specific checks are only described as passing after they have actually run successfully.

## First version

Pushing the source triggers GitHub Actions checks for Python tests, JavaScript syntax and the Docker build. Do not claim checks have passed for a new commit before their run completes.

The suggested version tag is `v0.1.0`; see [CHANGELOG.en.md](../CHANGELOG.en.md) for release notes. The source ZIP can be attached to a GitHub Release for users who prefer downloading an archive.

Publishing the source does not automatically create a public collaboration website. Each deployment has independent accounts and data; all teammates must connect to the same instance.
