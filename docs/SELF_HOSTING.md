# 自行部署指南

## 谁需要安装

只有提供服务的人需要下载项目并安装 Python 或 Docker。其他成员通过浏览器访问同一个服务地址，无需安装项目。

不同部署是不同系统，账号和文件互不相通。GitHub 托管源码，不会自动运行这套 Python 网站；本项目不能直接部署到 GitHub Pages。

## Windows

1. 安装 Python 3.10 或更新版本，启用安装器中的 Add Python to PATH。
2. 下载源码并解压到普通文件夹。
3. 双击 `start.bat`，保持打开的命令窗口运行。
4. 在浏览器打开 `http://127.0.0.1:8765`，注册自己的账号。未登录时的示例数据与真实账号分离。
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
