# Self-hosting guide

[简体中文](SELF_HOSTING.md) | **English**

## Who needs to install anything?

Only the host downloads the project and installs Python or Docker. Other members use a browser to visit the same service address. See the [user guide](USAGE.en.md) for registration, invitations, chat and files.

Separate deployments have separate accounts and data. GitHub hosts the source code; it does not automatically run this Python service. The app cannot run directly on GitHub Pages.

Choose **Code → Download ZIP** in the repository and extract it into a writable folder, or clone the repository with Git. Run from the extracted folder, not inside the ZIP. The source bundle contains no database, uploaded user files or experimental records. First startup creates an empty database. The app interface is currently in Simplified Chinese; this guide documents the same application in English.

## Choose a deployment method

| Method | Suitable for | If the host shuts down |
| --- | --- | --- |
| `start.bat` / `sh start.sh` | Trying it on your own computer | The website stops; saved disk data remains. |
| `start-lan.bat` / `--host 0.0.0.0` | A small team on a trusted LAN | All members lose access; saved data remains. |
| Docker Compose | A computer or server with Docker | The service still stops when the machine is off; the named volume remains. |
| Another continuously running server | Keeping the app available when your personal computer is off | Members can continue while that server and service stay available. |

Sleep, an exited server process or a disconnected network can also make the service unavailable. Closing a browser does not stop the server, but closing the ordinary startup script's terminal window stops that Python process. Run the script again after rebooting the host.

Compose sets `restart: unless-stopped`. Docker itself must start for this to help, and containers stopped manually need `docker compose start`. This restart policy does not keep a powered-off computer online.

Offline chat and offline access to server files are not supported. Use the original data directory or Docker volume after restarting to retain accounts and files. If the host's LAN IP changes, tell members the new address and generate invitations from that address.

## Windows

1. Install Python 3.10 or newer and enable **Add Python to PATH** in its installer.
2. Download and extract the source into a regular folder.
3. Double-click `start.bat` and keep its terminal window open.
4. Open `http://127.0.0.1:8765` and register. There is no default account, password, conversation or uploaded file.
5. Press Ctrl+C to stop the service. Closing the window also stops it. Run the launcher again to resume.

If the default port is occupied, run this from the project folder:

```powershell
python server.py --port 8767
```

## macOS / Linux

```sh
sh start.sh
```

Alternatively, run `python3 server.py`. In the remaining Python command examples, use `python3` if that is your system's Python command.

## Share on a trusted LAN

On Windows, double-click `start-lan.bat`, or run:

```sh
python server.py --host 0.0.0.0
```

Find the host's LAN IP, for example `192.168.1.20`. On Windows, run `ipconfig`. Everyone opens `http://192.168.1.20:8765` in their browser.

Allow the application or port through Windows Firewall only on the trusted private network. Sign in and generate invitations using the LAN address. Do not use `127.0.0.1` or `0.0.0.0` as a shared invitation address. Guest Wi-Fi isolation, different subnets and firewall rules may prevent access.

Turning off, sleeping or disconnecting the host prevents access but does not automatically delete its disk data. Access from outside the LAN requires additional network configuration; read [SECURITY.en.md](../SECURITY.en.md) before exposing the service publicly.

## Docker

Install and start Docker with Compose v2 support. From the project root:

```sh
docker compose up -d --build
docker compose logs -f
```

Open `http://127.0.0.1:8765`. By default, Compose binds only to the host's loopback interface and persists data in the `together-data` named volume.

For LAN access, create a `.env` file in the project root. Do not commit it:

```dotenv
TOGETHER_BIND=0.0.0.0
TOGETHER_PORT=8765
COOKIE_SECURE=0
```

Run `docker compose up -d` again, then open the host's LAN address.

Common commands:

```sh
docker compose stop
docker compose start
docker compose down
```

`down` retains the named volume. **Do not run `docker compose down -v` to stop the service:** it deletes the data volume, including accounts, messages, uploaded files and backups.

## Configuration

| Setting | Default | Meaning |
| --- | --- | --- |
| `--host` | `127.0.0.1` | Listen address; use `0.0.0.0` for LAN access |
| `--port` | `8765` | HTTP port |
| `WORKSPACE_DATA` | Project's `data/` folder | Data directory used by the server and maintenance tool |
| `COOKIE_SECURE` | `0` | Set to `1` for HTTPS; keep `0` for local HTTP |
| `TOGETHER_BIND` | `127.0.0.1` | Compose only: host binding address |
| `TOGETHER_PORT` | `8765` | Compose only: host port |

Direct Python startup does not automatically read `.env`. In PowerShell, set a custom data directory with `$env:WORKSPACE_DATA = 'D:\TogetherData'`. Compose reads its `.env` configuration itself.

## Where the data actually lives

- **Direct Python:** the default database is `data/workspace.db` under the source folder. It contains accounts, workspace membership, friends, messages, folders, all uploaded file bytes, file versions and trash. Startup creates missing directories and database tables.
- **Custom directory:** `WORKSPACE_DATA` points to a directory; its database is `workspace.db` inside that directory. Use the same environment setting for the server, maintenance commands and later restarts. An absolute path is recommended.
- **Docker:** the database is `/app/data/workspace.db` in the container, persisted in the `together-data` named volume. Its actual name usually looks like `<project>_together-data`. Docker manages this storage; it may not appear in the source folder. Use `docker volume ls` to find it, then `docker volume inspect <actual-volume-name>`. On Windows/macOS, it is typically managed inside Docker's Linux environment.
- **Backups:** snapshots are in the data directory's `backups/` folder and contain accounts, messages and file contents. Protect both the live database and backups; do not publish them.
- **Browser:** login cookies identify a session. Drafts and page state are not reliable backups. Explicitly downloaded files are saved in the downloading user's local downloads directory.

Personal, group-only and workspace-shared files have different application permissions, but share the same database. There is no end-to-end encryption. Neither the GitHub source nor the Docker image includes data created after deployment.

SQLite may create `workspace.db-wal` and `workspace.db-shm` while running. Use the backup command below for a consistent snapshot; do not copy only the main database while the service is running. Back up before deleting source files, and retain `data/` during upgrades.

A hosting platform with only ephemeral disk storage cannot preserve this app's data as-is. Configure persistent storage or adapt the database and file storage before using such a platform.

## Back up, restore and upgrade

For a direct Python deployment:

```sh
python maintenance.py backup
```

The command writes a snapshot to the data directory's `backups/` folder. Copy backups to another device regularly. Stop the service before restoring, and replace the example with an actual backup:

```sh
python maintenance.py restore "data/backups/your-backup.db"
```

Create a backup while the Docker service is running:

```sh
docker compose exec together python maintenance.py backup
```

The command prints the container's backup path. Export it using an actual path:

```sh
docker compose cp together:/app/data/backups/your-backup.db ./backup.db
```

Backing up only the image does not back up the named volume.

For Docker restore, stop the service and mount your backup into a one-off container using the existing data volume:

```sh
docker compose stop
docker compose run --rm -v "./backup.db:/tmp/restore.db:ro" together python maintenance.py restore /tmp/restore.db
docker compose start
```

Restore saves a snapshot of the previous database and invalidates existing sessions. Restore using the same application version or a compatible one.

Before upgrading, back up, stop the service, replace the source and retain the original `data/`. For Docker, rebuild with `docker compose up -d --build` while retaining the volume. Do not run an older application against an upgraded database; use a pre-upgrade backup when rolling back.

## Current limits

- Maximum upload: 10 MB per file. UTF-8 text previews: up to 1 MB; download other files to open them locally.
- Databases and backups consume the host's disk space. Backups are not automatically pruned.
- Chat refreshes approximately every 2.5 seconds. This release is intended for small-team trials, with no large-scale concurrency guarantee.
- No account recovery, email verification, total storage quota or login rate limiting.
- No simultaneous editing, online code execution or Git synchronization.
