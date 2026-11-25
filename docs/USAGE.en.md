# User guide

[简体中文](USAGE.md) | **English**

## First visit

The host follows the [self-hosting guide](SELF_HOSTING.en.md), starts the service and shares its reachable address. Everyone registers at **the same address**. Teammates do not need to download or install the project. There is no default administrator, default password or preloaded test account.

The interface is currently in Simplified Chinese. The Chinese labels below help you find the corresponding controls; selecting English documentation does not translate the app interface.

Click **登录 / 注册** (Sign in / Register). Enter your nickname, email address and a password of at least eight characters. Email is used for login and friend lookup; the app does not send verification messages or provide email password recovery. Keep your password safe. Accounts are not shared between different deployments.

## Create a project and invite teammates

1. On **主页** (Home), click **创建工作区** (Create workspace) under **工作区** (Workspaces), then name the project.
2. Select the workspace. Its file library opens on the right, where you can upload files and create folders.
3. Click **创建群聊** (Create group) under **群聊** (Groups). Select the workspace and choose who can view the group.
4. As the group owner, open **查看成员 → 邀请加入本群** (View members → Invite to this group) in the chat header. Generate a link and send it to your teammates. They register or sign in at the same service address, review the access scope and click **确认加入** (Confirm join).

Generate invitations using a LAN address or website address your teammates can reach. `127.0.0.1` points to the computer running the browser, so sharing that address does not connect someone else to your host.

A workspace stores shared project files; a group stores a conversation. Multiple groups linked to one workspace see **the same workspace file library**. A group invitation also grants access to the linked workspace's files and public groups, so confirm those materials are suitable for the invitee. Other private groups still require separate invitations.

## Chat and friends

- Select a group on Home and type on the right. Enter sends a message; Shift+Enter inserts a new line.
- Open **好友** (Friends) and add someone using the email they registered on this instance. After they accept, you can exchange direct messages.
- Messages support replies, code blocks, @ mentions, bookmarks and pins. Group owners can remove members. A direct-message header includes a remove-friend action.
- **查找记录** (Search history) in the chat header filters by keyword, date and messages/files. File keywords search filenames, not file contents.
- Chat requires the service to be online. Retry failed sends as prompted; offline sending is not supported.

## File locations and access

| Where you put a file | Who can access it through the app |
| --- | --- |
| Home's workspace or **团队共享** (Team shared) on the Files page | All members of that workspace |
| A linked group's upload with **添加到工作区文件库** (Add to workspace library) | All workspace members; other linked groups see it in the same library |
| A group upload with **仅保存到本群附件库** (Save only to this group's attachment library) | Current members of that group |
| An independent group's attachments | Current members of that group |
| Direct-message attachments | The two users while their friend relationship is active |
| **我的文件工作区** (My file areas) on the Files page | Your account |

These are application access rules. The actual file bytes are stored together in the host's database, which the host operator can read. Files are not automatically copied to every member's computer or synchronized to GitHub.

The chat header's **本群附件** (Group attachments) opens group-only files. In **查找记录** (Search history), the file scope can also select **工作区文件库** (Workspace library) or **本群聊天中的全部附件** (All attachments in this group's chat). Message search always stays within the current conversation.

When a filename already exists, keep both copies, such as `notes.md` and `notes (2).md`, or update the original and retain its previous version. A file's `…` menu supports rename, move, versions and trash. Maximum upload size is 10 MB per file. UTF-8 text previews support up to 1 MB; download other files and open them with local software.

## Returning later and keeping your data

Members reopen the original address and sign in. The host machine must remain powered on, connected and running the service. If it shuts down, members cannot use the app. Starting the original service again makes previously saved data available. Closing one member's browser does not stop the server.

Default storage is `data/workspace.db` under the deployment folder, with backups in `data/backups/`. Docker uses a persistent named volume. Personal files, attachments, versions and messages are all included in the database. See the [self-hosting guide](SELF_HOSTING.en.md) for migration, backups, restore and upgrades. Do not delete the data directory or expect accounts to appear automatically in another empty deployment.

Simultaneous editing, online code execution and Git synchronization are not implemented. Uploaded source code can be stored, previewed and downloaded; the app does not execute it.
