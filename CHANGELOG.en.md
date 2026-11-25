# Changelog

[简体中文](CHANGELOG.md) | **English**

## 0.1.0 — 2026-11-25

First self-hosted source release.

- Chinese and English README, deployment, usage, contributing, security and publishing guides, plus changelog, with links to switch languages. The application UI remains in Simplified Chinese.
- Source bundles exclude databases and experimental data. Signed-out visitors see a welcome page and sign-in entry, with no preloaded sample friends, conversations or files.
- Deployment and user guides explain shutdown behavior, storage locations, persistent volumes, backup/restore and joining a team.
- Blue, white and black three-column interface; registration, login, personal files and shared workspaces.
- Separate workspaces and group chats: independent groups, invitation-only groups and workspace-public groups.
- Group invitations with access previews, member removal, friend requests, direct messages and friend removal.
- Quoted replies, bookmarks, conversation pins, @ mentions, unread counts and read positions.
- Message/file history search by keyword and date, pagination and surrounding-message context.
- Group-only or workspace-shared attachments, with file search scoped to the selected library.
- Nested folders, previews, downloads, numbered duplicate filenames, file versions and trash.
- Message/upload retry deduplication and connection status.
- Automatic/manual SQLite backups, offline restore and server locking.
- Windows launchers, Docker configuration, automated checks and allowlisted source packaging that excludes user data.

Not implemented: simultaneous editing, code execution, Git synchronization, account recovery, email notifications and workspace-member removal.
