# Security and deployment scope

[简体中文](SECURITY.md) | **English**

This release targets local computers, trusted LANs and small-team trials. It is not a complete public multi-tenant service. It uses Python's standard-library HTTP server and lacks account recovery, login rate limiting, email verification, total storage quotas and comprehensive auditing. Do not expose it directly to the internet without hardening it.

## Data and access

- The database contains accounts, password hashes, sessions, invitations, messages and file contents. Backups are equally sensitive. Restrict disk access and keep separate backups. There is no end-to-end encryption; the host operator can access the database.
- A group invitation can also grant access to all files and public groups in its linked workspace. The join preview explains this scope.
- Group-only attachments follow group access rules. Workspace-shared attachments are available to all workspace members, including files uploaded from a private group when the uploader chooses workspace sharing.
- Removing someone from a group does not remove their workspace membership. They retain access to workspace-shared files but lose the removed group's private attachments and conversation.
- Uploaded HTML, scripts and source code are stored as files or shown as text previews. This application does not execute them.
- Never publish passwords, cookies, complete invitation links, databases or backups containing personal information in issues, screenshots or logs.

## Before public deployment

Provide an HTTPS reverse proxy and a suitable production service architecture, login rate limiting, registration controls, quotas, tested backup/restore procedures and access monitoring. Set `COOKIE_SECURE=1` when serving through HTTPS. Keep it disabled for local HTTP testing.

## Reporting vulnerabilities

Do not post exploitable vulnerability details or sensitive data in a public issue. If the repository has GitHub private vulnerability reporting enabled, use **Report a vulnerability** on its Security page. Otherwise, open a contact request without exploit details so the maintainer can arrange a private communication channel.
