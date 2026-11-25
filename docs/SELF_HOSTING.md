# 自行部署指南

**简体中文** | [English](SELF_HOSTING.en.md)

## 谁需要安装

只有提供服务的人需要下载项目并安装 Python 或 Docker。其他成员通过浏览器访问同一个服务地址，无需安装项目。

不同部署是不同系统，账号和文件互不相通。GitHub 托管源码，不会自动运行这套 Python 网站；本项目不能直接部署到 GitHub Pages。

在 GitHub 仓库点击 **Code → Download ZIP** 后解压；也可以使用 Git 克隆源码。不要把 ZIP 文件直接当作运行目录，先解压到可写文件夹。初始发布包不带数据库、用户上传资料或实验记录；第一次启动会建立空数据库。注册、邀请、聊天和文件操作见 [使用指南](USAGE.md)。

## 选择运行方式与关机影响

| 方式 | 适合场景 | 部署机器关机后 |
| --- | --- | --- |
| `start.bat` / `sh start.sh` | 自己在本机试用 | 网站停止，已保存的磁盘数据保留 |
| `start-lan.bat` / `--host 0.0.0.0` | 同一受信任局域网多人协作 | 所有成员无法连接，数据保留 |
| Docker Compose | 有 Docker 的常开电脑或服务器 | 机器关机仍会停止服务；命名卷数据保留 |
| 部署到另一台持续运行的服务器 | 希望自己的电脑关机后伙伴仍能使用 | 只要那台服务器在线且服务正常，伙伴可以继续使用 |

电脑休眠、服务进程退出、网络中断也可能让成员无法连接。关闭浏览器不会停止后台服务，但关闭启动脚本的命令窗口会停止普通 Python 启动方式。机器重启后需重新运行启动脚本；Docker 配置了 `unless-stopped` 重启策略，仍要求 Docker 本身启动，手动停止过的容器需用 `docker compose start` 启动。

当前不支持离线聊天或离线浏览服务器文件。重启后如要保留原账号和文件，必须使用原数据目录或原 Docker 数据卷；局域网 IP 改变时需把新网址告知成员，并在新网址重新生成邀请。

## Windows

1. 安装 Python 3.10 或更新版本，启用安装器中的 Add Python to PATH。
2. 下载源码并解压到普通文件夹。
3. 双击 `start.bat`，保持打开的命令窗口运行。
4. 在浏览器打开 `http://127.0.0.1:8765`，注册自己的账号。新部署没有默认账号、聊天或文件；未登录时显示登录入口。
5. 用 Ctrl+C 停止服务；关闭窗口也会停止服务。再次双击启动即可继续使用。

端口被占用时，在项目目录的终端运行：

```powershell
python server.py --port 8767
```

## macOS / Linux

```sh
sh start.sh
```

也可以直接使用 `python3 server.py`。

## 同一局域网多人使用

Windows 双击 `start-lan.bat`，或运行：

```sh
python server.py --host 0.0.0.0
```

在部署电脑查找局域网 IP（Windows 可在终端使用 `ipconfig`），例如 `192.168.1.20`。所有人访问 `http://192.168.1.20:8765`。

在 Windows 防火墙中仅为受信任的专用网络允许该程序或端口。使用上述局域网网址登录并生成邀请；不要把 `127.0.0.1` 或 `0.0.0.0` 当作邀请网址。跨网段、访客 Wi-Fi 隔离或防火墙规则可能阻止连接。

部署电脑关机、休眠或断网时，其他成员无法访问；其磁盘上的数据不会因此自动删除。外网访问需要额外配置网络入口，公网使用前请阅读 `SECURITY.md`。

## Docker

需要安装并启动 Docker，支持 Compose v2。项目根目录运行：

```sh
docker compose up -d --build
docker compose logs -f
```

打开 `http://127.0.0.1:8765`。默认仅监听本机，数据写入 `together-data` 命名卷。

如需局域网访问，在项目根目录创建 `.env` 文件（不要提交到仓库）：

```dotenv
TOGETHER_BIND=0.0.0.0
TOGETHER_PORT=8765
COOKIE_SECURE=0
```

然后重新运行 `docker compose up -d`，通过部署电脑的局域网地址访问。

常用命令：

```sh
docker compose stop
docker compose start
docker compose down
```

`down` 保留命名卷；**不要执行 `docker compose down -v`**，它会删除容器数据卷，包括聊天、账号、文件和备份。

## 配置

| 项目 | 默认值 | 说明 |
| --- | --- | --- |
| `--host` | `127.0.0.1` | 监听地址；局域网用 `0.0.0.0` |
| `--port` | `8765` | HTTP 端口 |
| `WORKSPACE_DATA` | 项目下 `data/` | 服务及维护工具的数据目录 |
| `COOKIE_SECURE` | `0` | HTTPS 部署设为 `1`，本机 HTTP 保持 `0` |
| `TOGETHER_BIND` | `127.0.0.1` | 仅 Docker Compose 使用，控制宿主机绑定地址 |
| `TOGETHER_PORT` | `8765` | 仅 Docker Compose 使用，控制宿主机端口 |

直接运行 Python 时不会自动读取 `.env`。在 PowerShell 中使用 `$env:WORKSPACE_DATA = 'D:\TogetherData'` 设置自定义数据目录；Docker 的 `.env` 由 Compose 读取。

## 数据实际保存位置

- 直接运行 Python：默认位于源码目录的 `data/workspace.db`。账号、工作区成员、好友、聊天、文件夹、全部上传文件的内容、历史版本与回收站均在同一 SQLite 数据库中。服务器启动会创建缺失的目录和数据库。
- 自定义路径：`WORKSPACE_DATA` 指向数据文件夹，数据库为该文件夹下的 `workspace.db`。服务与维护命令要使用同一环境变量；建议设置绝对路径，并在下次启动时保持相同配置。
- Docker：数据位于容器 `/app/data/workspace.db`，由 `together-data` 命名卷持久保存；实际卷名通常为 `<项目名>_together-data`。这是 Docker 管理的存储，不一定出现在源码目录；可用 `docker volume ls` 查看卷，再用 `docker volume inspect <实际卷名>` 检查。Windows/macOS 上通常由 Docker 的 Linux 虚拟环境管理。
- 备份：数据目录的 `backups/`，每份快照包含账号、聊天与文件内容。数据库和备份都需要保护，不能公开上传。
- 浏览器：保存登录 Cookie；输入中的草稿和界面状态不是可靠备份。点击下载的文件另存到下载者电脑的下载目录。

「个人文件」「仅本群」「工作区共享」决定谁可以通过网站访问，不代表不同的磁盘存储位置，也不提供端到端加密。GitHub 源码、Docker 镜像都不包含运行后生成的数据。

SQLite 运行时可能产生 `workspace.db-wal` 和 `workspace.db-shm`。使用下节备份命令获得一致的快照，不要在运行中仅复制主数据库文件。删除源码前先备份；升级时保留 `data/`。免费托管平台如果只提供临时磁盘，不能直接保证本项目数据持久保存，必须先配置持久化存储或改造数据库与文件存储。

## 备份、恢复与升级

直接运行 Python 时：

```sh
python maintenance.py backup
```

备份输出到数据目录的 `backups/`，请定期复制到其他设备。恢复前停止服务，在项目目录运行（替换为实际路径）：

```sh
python maintenance.py restore "data/backups/实际备份.db"
```

Docker 运行中可生成备份：

```sh
docker compose exec together python maintenance.py backup
```

命令会输出容器内备份路径，使用 `docker compose cp together:/app/data/backups/实际备份.db ./备份.db` 导出。不要只备份容器镜像，镜像不包含命名卷数据。

Docker 恢复时先停止服务，把备份复制到数据卷，再执行恢复工具：

```sh
docker compose stop
docker compose run --rm -v "./备份.db:/tmp/restore.db:ro" together python maintenance.py restore /tmp/restore.db
docker compose start
```

恢复会保存原数据库快照并使已有登录失效。请使用同版或兼容版本的应用恢复。

升级前先备份，再停止服务并替换源码，保留原有 `data/`；Docker 使用 `docker compose up -d --build` 重建，保留命名卷。不要用旧版本覆盖已升级数据库；回退时使用升级前备份。

## 当前限制

- 单文件最大 10 MB；UTF-8 文本预览最大 1 MB，其他文件下载查看。
- 数据库及备份占用部署电脑磁盘，备份不会自动清理。
- 聊天约每 2.5 秒刷新，适合小团队试用，没有大规模并发性能承诺。
- 没有账号找回、邮件验证、总存储配额和登录限流。
- 尚无多人编辑、在线运行代码、Git 同步。
