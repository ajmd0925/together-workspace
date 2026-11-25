# Contributing

[简体中文](CONTRIBUTING.md) | **English**

Issues and improvements are welcome. Read the [README](README.en.md) and [security notes](SECURITY.en.md) first.

## Local development

Use Python 3.10+; no third-party Python packages are required. Refresh the browser after changing frontend source files. Node.js is only needed for JavaScript syntax checks.

```sh
python server.py
python -m unittest discover -s tests -v
node --check public/shared.js
node --check public/features.js
node --check public/client.js
```

Tests automatically create accounts and databases in temporary directories. Never use a real workspace for deletion, invitation or upload testing.

## Project layout

- `server.py`: HTTP service, accounts, original database schema and basic API.
- `collaboration.py`: group access, chat, attachments, search and file management.
- `maintenance.py`: backup, restore and server locking.
- `public/`: vanilla JavaScript/CSS interface; see `index.html` for script loading order.
- `tests/`: integration and backup/restore tests; `preview_fixture.py` is an isolated temporary browser-test service.
- `scripts/prepare_release.py`: packages public source files using an explicit allowlist.

## Submitting changes

Describe the problem, actual behavior, resulting change and how you verified it. Permission and database changes need relevant tests and compatibility with existing data. Do not resolve permission issues by silently widening access.

Do not commit `data/`, databases, backups, passwords, session cookies, invitation links, private files or other user data. The interface and documentation must distinguish planned features from implemented ones.

## Documentation languages

Chinese documents use the original filenames; English versions use `.en.md`. Keep both versions' behavior, limits and commands aligned, and preserve their language-switch links. The application UI is currently in Simplified Chinese; documentation translation does not imply UI localization.

Add new public documents to `SOURCES` in `scripts/prepare_release.py`. Regenerate the source bundle and its SHA-256 manifest after editing release files; do not edit an old manifest to hide a mismatch.
