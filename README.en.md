# Together · 同频

[简体中文](README.md) | **English**

A simple collaboration web app with a blue, white and black three-column layout: navigation on the left, workspaces and conversations in the middle, and chat or files on the right.

**v0.1.0 · MIT licensed · Self-hosted · Python 3.10+ · SQLite · Vanilla JavaScript/CSS**

Designed for individuals and small teams on a local computer or trusted LAN. No paid service or third-party Python package is required. Only the host needs Python; teammates use their browsers to access the same instance. Accounts, messages and uploaded files are stored on the host machine.

Documentation is available in Chinese and English. **The application interface is currently in Simplified Chinese.** Both documentation languages describe the same application; there is no separate installation. Collaborative editing, code execution and Git synchronization are not implemented.

## Features

| Area | Available features |
| --- | --- |
| Communication | Group chats, friend requests, direct messages, inviting and removing group members, removing friends |
| Chat tools | Replies, @ mentions, unread counts, bookmarks, pins and history search |
| Files | Shared and personal folders, group-only attachments, uploads, previews and downloads |
| Recovery | Numbered duplicate names, file versions, trash and database backups |
| Ownership | Each deployment keeps its own accounts and data |

Start with the [self-hosting guide](docs/SELF_HOSTING.en.md) and [user guide](docs/USAGE.en.md). See also [contributing](CONTRIBUTING.en.md), [publishing to GitHub](docs/GITHUB_RELEASE.en.md), the [changelog](CHANGELOG.en.md) and [security notes](SECURITY.en.md).

## Download and invite your team

1. On the GitHub repository, choose **Code → Download ZIP**, extract the files and install Python as described below.
2. For your own computer, double-click `start.bat`. For a trusted LAN on Windows, double-click `start-lan.bat`.
3. Share the host's reachable address, such as `http://192.168.1.20:8765`. Teammates open that address in a browser, register an account and follow an invitation to join a workspace or group.
4. Everyone must connect to the same instance. Running separate copies on different computers creates separate accounts and data; those copies do not synchronize.

This repository provides self-hosted software, not a public hosted service or a shared account system. Downloading the source, publishing it on GitHub or running Docker in the background does not keep a powered-off computer online.

## What happens when the host is turned off?

| Situation | Can teammates continue using the app? |
| --- | --- |
| The app runs on your computer, and that computer shuts down, sleeps, disconnects or stops the service | No. Chat, uploads and access to server files are unavailable. |
| The app runs on another computer or server that stays online, and your own computer shuts down | Yes, as long as that host and its service remain available. |
| You close your browser, but the host and service keep running | Other members can continue. You can reopen the address later. |
| The host restarts and the app starts with its original data directory | Previously saved accounts, messages and files remain available. |

Text already displayed may remain on screen, but offline collaboration and sending new messages while disconnected are not supported. Stopping the service does not automatically delete data on disk. Deleting the database or Docker data volume does delete stored data. With the ordinary startup scripts, start the service again after rebooting the host.

## Start the app

On Windows, install Python 3.10+, extract the project and double-click `start.bat`. On macOS or Linux, run `sh start.sh`. You can also run:

```sh
python server.py
```

Open `http://127.0.0.1:8765` and register or sign in. A fresh installation starts empty: there are no preloaded test accounts, messages or files. Visitors see a welcome page with a sign-in entry.

For a trusted LAN, run:

```sh
python server.py --host 0.0.0.0
```

Open the host's LAN address before generating invitations. Allow the port through the host's firewall on the trusted network. `127.0.0.1` refers to the computer running the browser and cannot be shared as the address of your host. The host must stay on and connected. GitHub stores the source; it does not run this Python service for you.

Docker configuration is also included:

```sh
docker compose up -d --build
```

By default, Docker binds only to the local computer and persists data in a named volume. See the [self-hosting guide](docs/SELF_HOSTING.en.md) for LAN access, configuration, stopping the service and backups.

## Workspaces, groups and access

- A **workspace** holds shared project files and folders. Members can access its files and workspace-public groups.
- A **group** holds a conversation. It can be linked to a workspace or created independently. New groups default to invited members only; linked groups can also be visible to the entire workspace.
- Several groups linked to one workspace share **one workspace file library**. The workspace button in a linked group's header opens it.
- When uploading a group attachment, choose group-only storage or the linked workspace library. Group-only files are available to current group members; workspace files are available to all workspace members. Independent groups only support group-only storage. Existing files retain their original sharing scope.
- Group owners can generate invitations valid for seven days. **An invitation to a linked group also grants access to all files and public groups in its workspace.** Other private groups require their own invitations. Workspace owners can generate workspace invitations, which grant access to workspace files and public groups.
- Invitees see the access scope and must explicitly confirm before joining.
- Group owners can remove other members, but not the owner. Removed members lose that group's messages, search and group-only attachments, including access inherited from workspace-public visibility. Their workspace membership and other groups remain. Removal invalidates all existing invitations to that group; a new valid invitation can bring the member back.
- Groups from older installations retain their original workspace-public visibility and existing data.
- Add friends using their registered email address. After acceptance, direct messages and attachments are accessible to the two friends.
- Removing a friend ends the relationship for both users and blocks direct messaging, history search and attachment access. History is retained and becomes accessible again after a new request is accepted. Shared groups and workspace access remain.
- Personal file areas are private to the account. Workspace files and the Files page's team-shared area are shared with workspace members.

## Chat and search

- Group and friend lists show unread counts and @ mentions. Select a member using the @ button, or type `@nickname` followed by a space or punctuation.
- Read positions are saved on the server. Opening a conversation locates unread messages within the latest 500 messages. Use history search for older records. Scroll positions are retained when switching conversations in the same page.
- Pin workspaces, groups or friends to sort your own lists. Message pins are visible to conversation members. Messages also support quoted replies, code blocks and personal bookmarks.
- Group chats and direct messages support attachment cards, previews and downloads. The upload limit is 10 MB per file; UTF-8 text previews are limited to 1 MB.
- History search covers the full conversation and combines keywords, start/end dates and message/file filters. File keywords match **filenames**, not file contents. Dates use the browser's local time zone and include the entire end date. Results load in reverse chronological pages.
- Search results and quoted messages can open surrounding messages. A group's attachment button opens its group-only library. File search can cover group-only files, all attachments in that group's chat, or the linked workspace library. Workspace scope includes direct uploads and files shared by other linked groups, but excludes other groups' private attachments. Message search always stays within the current conversation.
- Failed sends retain input for retry. Messages and uploads use retry identifiers to avoid duplicates after a lost response. Failed uploads offer a retry action. Connection status appears below the lists; chat and activity refresh approximately every 2.5 seconds.

## Organize and recover files

- Personal and shared workspace files support nested folders. Use the file's `…` menu to rename, move, inspect versions or move it to trash.
- Folders can be renamed or moved, but cannot be moved into themselves or their descendants.
- For a duplicate filename, keep both files, such as `notes.md` and `notes (2).md`, or update the existing file while retaining its previous version.
- Restoring a version first saves the current contents, then creates a new version.
- Trash supports viewing and restoring files, without a permanent-delete action. Personal trash covers your personal files; workspace trash covers the current workspace. Restored files return to their original folder.
- All workspace members can organize workspace files. Independent-group and direct-message attachments do not currently have folder-management controls.

## Data and backups

**The host machine** stores accounts, conversations, file contents and versions in `data/workspace.db`. Personal and group-only files use the same database with different application permissions. A stored filename does not mean a matching file exists in the source directory. Passwords use salted hashes. There is no end-to-end encryption, so the host operator must protect the database.

| Data | Default location |
| --- | --- |
| Accounts, friends, workspaces, groups, messages, folders and permissions | `data/workspace.db` |
| Workspace and personal files, group/direct-message attachments, versions and trash | The same `data/workspace.db`, including the actual file bytes |
| Automatic and manual backups | `data/backups/*.db`; each snapshot includes accounts and file contents |
| Docker data | The Compose `together-data` named volume, mounted at `/app/data`; its actual name usually has a project prefix |
| Files downloaded through a browser | The downloading user's local downloads directory |

Set `WORKSPACE_DATA` to change the data directory. Browser login cookies identify a session and are not a backup. Drafts and page state are not reliable saved records; rely on a successful send or upload. SQLite may create `workspace.db-wal` and `workspace.db-shm` while running. Use the backup command rather than copying only the live main database. Do not commit databases or backups to Git.

The service snapshots an old database before upgrading it. It also creates an automatic daily backup on the first startup of a day or when the running service crosses into a new day. Backups use SQLite's snapshot API and are checked for integrity. They stay on the host and are not automatically pruned; copy them to another device and monitor available disk space.

Create a manual backup:

```sh
python maintenance.py backup
```

Stop the server before restoring, then replace the example with an actual backup path:

```sh
python maintenance.py restore "data/backups/your-backup.db"
```

Restore validates the backup, saves a snapshot of the current database and refuses to run while the server holds the data lock. Restart afterward; all users must sign in again.

## Validation

```sh
python -m unittest discover -s tests -v
node --check public/client.js
node --check public/shared.js
node --check public/features.js
```

Tests create temporary databases and accounts. They cover access isolation, invitations, history search, direct-message attachments, unread positions, mentions, retry deduplication, bookmarks, replies, folders, versions, trash and backup/restore. `python tests/preview_fixture.py` starts an isolated temporary browser-test server at `127.0.0.1:8766`; its test data is disposable and separate from the application's data.

## Public deployment limitations

This is a local/trusted-LAN collaboration release, not a ready-to-run public multi-tenant service. Account recovery, email delivery, login rate limits, total storage quotas, workspace-member removal and a separate invitation-revocation management screen are not implemented. Neither are collaborative editing, online code execution or Git synchronization.

Before public deployment, address these gaps, use HTTPS and a suitable production service architecture, and keep off-host backups. Set `COOKIE_SECURE=1` when serving over HTTPS. Read [SECURITY.en.md](SECURITY.en.md).

## License

[MIT License](LICENSE), copyright Together contributors. Preserve the license when redistributing the project.
