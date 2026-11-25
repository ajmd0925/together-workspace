# 参与开发

欢迎提交问题和改进。请先阅读 README 和 SECURITY。

## 本地开发

使用 Python 3.10+，无需安装第三方 Python 包；修改前端源文件后刷新浏览器即可。Node.js 仅用于检查 JavaScript 语法。

```sh
python server.py
python -m unittest discover -s tests -v
node --check public/shared.js
node --check public/features.js
node --check public/client.js
```

测试账号和数据库由测试自动创建在临时目录中。不要使用真实工作区做删除、邀请或上传测试。

## 目录

- `server.py`：HTTP 服务、账号、原始数据库结构和基础 API。
- `collaboration.py`：群权限、聊天、附件、查找及文件管理。
- `maintenance.py`：备份、恢复、运行锁。
- `public/`：原生 JavaScript/CSS 界面；加载顺序见 `index.html`。
- `tests/`：集成与备份恢复测试；`preview_fixture.py` 是临时页面测试服务。
- `scripts/prepare_release.py`：按清单打包可公开发布的源文件。

## 提交改动

请描述问题、实际行为、改动和验证方式。权限及数据库变更需要补充相应测试，兼容已有数据，不能通过默认扩大共享范围解决问题。

不要提交 `data/`、数据库、备份、密码、会话 Cookie、邀请链接、私人文件或其他用户资料。界面与 README 不应将计划中的功能写成已实现。
