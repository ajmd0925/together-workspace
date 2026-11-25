# 发布到 GitHub

**简体中文** | [English](GITHUB_RELEASE.en.md)

## 准备目录

维护者在项目根目录运行：

```sh
python scripts/prepare_release.py
```

脚本从明确的文件清单生成 `release/together-workspace-v0.1.0/` 和同名 ZIP，已有产物不会覆盖，重复生成时追加时间戳。包含源码、中英文文档、启动及部署配置、测试、MIT 许可证和 SHA-256 文件清单。

不包含 `data/`、数据库、备份、会话、用户上传资料、`.env`、本机路径配置、缓存、旧前端原型和上级 Git 仓库历史。运行发布目录中的服务后会生成新的 `data/`，上传前仍需确认其未被提交。

## 创建仓库

建议仓库名 `together-workspace`，描述：

> 简洁的团队协作工作区：群聊、私聊、共享文件、群附件与历史查找，支持自行部署。

如果使用已准备的发布目录初始化仓库，创建空仓库即可，README、LICENSE 和 `.gitignore` 已在发布目录中。仓库可见性由维护者选择。

使用 Git 或 GitHub Desktop 发布**生成目录中的文件**，不要在更大的上级项目目录执行整体上传。如果用网页上传，需要注意隐藏的 `.github/`、`.gitignore`、`.dockerignore` 也应包含在内。不要只上传一个 ZIP，仓库主页需要可直接浏览的源码和 README。

仓库默认 README 为中文，读者点击顶部的 **English** 打开 `README.en.md`；每份英文文档也能切换回对应中文页。两种语言使用同一份程序和数据模型。

创建后可把仓库地址交给开发助手，再连接远程并检查待上传文件。发布前确认：

- 文件列表没有 `data/`、`.db`、备份、会话、密码或私人资料。
- README、LICENSE 和启动脚本位于仓库根目录。
- 中英文文档和相对链接完整，均已纳入发布文件清单。
- `python -m unittest discover -s tests -v` 通过，JavaScript 语法检查通过。
- Docker 和跨平台运行由相应环境实测；自动检查实际通过后再宣称通过。

## 首次版本

推送代码后，GitHub Actions 将检查 Python 测试、JavaScript 语法和 Docker 构建。工作流尚未在 GitHub 执行时不要把检查状态写成已通过。

建议版本标签 `v0.1.0`，发布说明见 `CHANGELOG.md`。可将准备好的 ZIP 附加到 Release，方便不熟悉 Git 的用户下载。

这是自行部署软件的源码发布，不会自动生成公网协作网站。每套部署使用独立账号和数据；所有团队成员需连接同一实例。
