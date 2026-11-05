# personal-pm-web

多人使用的个人项目管理。项目、任务和费用按工作区隔开，打开浏览器就能用。

界面来自本地版 [personal-pm](https://github.com/leonjianghao1900/personal-pm)。本仓库是它的云端版：后端跑在 Cloudflare 上，数据放在 D1 和 R2 里。

## 这是什么

*What it is*

这是一套个人项目管理（可建多个 workspace）。服务跑在 Cloudflare Workers 上，业务数据在 D1，附件在 R2，界面是 Vue 单页应用。

每个人用邮箱和密码登录。普通用户属于一个工作区，看这个工作区里的项目。管理员可以新建工作区，并把用户分配进去。多名用户可以共用同一个工作区，看到的是同一份数据。

## 线上入口

*Live app*

<https://personal-pm-web.leondoubao.workers.dev>

还没有自定义域名。第一次用管理账号时，如果还没有工作区，先建一个工作区再把自己加进去。

## 核心能力

*Features*

- **项目和任务。** 项目列表、任务详情、子任务、里程碑、进度、优先级，以及甘特图。任务之间可以设依赖。
- **多个工作区。** 业务数据都带工作区。别的工作区的记录一律当作不存在，不会告诉你它在不在。
- **邮箱密码登录。** 密码用 PBKDF2-HMAC-SHA256 保存。登录后发 HS256 JWT，放在 HttpOnly 的 `pm_session` cookie 里。HTTPS 上这个 cookie 带 `Secure`。
- **管理员。** 角色只有管理员和普通用户。管理员可以创建工作区、创建用户，并把用户分到某个工作区。普通用户必须属于一个工作区。
- **费用。** 费用和费用类别按项目记录，可以导出 Excel。
- **收件箱和总览。** 收件箱用来快速记下事项；总览看当前工作区的概况。
- **附件。** 文件传到 R2。对象按工作区分开存放，数据库里只记相对路径。
- **备份。** 可以导出当前工作区的完整 ZIP（数据表加上对应附件）。恢复时只替换这一个工作区，并重写 id，避免和别的工作区撞号。另有不含文件的 JSON 备份。格式兼容 personal-pm 备份版本 1–3。

登录后可以在「设置」里修改密码。

## 技术栈

*Stack*

- **计算：** Cloudflare Workers 上的 Python ASGI，接口按 FastAPI 风格来写
- **数据库：** D1（一套库，表上有 `workspace_id`）。本地开发用 SQLite 文件，SQL 与线上相同
- **附件：** R2。本地开发用 `data/blobs/` 代替
- **前端：** Vue 3、Vue Router、Pinia、Vite。构建结果作为 Workers Static Assets 提供

## 和本地版的区别

*Compared with personal-pm*

[leonjianghao1900/personal-pm](https://github.com/leonjianghao1900/personal-pm) 是本地版，数据在本机 SQLite。

本仓库是云端 Workers 版：同一套使用方式放到 Cloudflare 上，用 D1 和 R2 代替本地数据库和本地文件，并加上多工作区和账号。两个仓库各管各的，这里不会改本地版仓库。

## 本地运行

*Run locally*

需要 Python 3.12+ 和 Node 18+。

```bash
python3 -m venv .venv
.venv/bin/pip install fastapi 'pydantic>=2' python-multipart openpyxl 'uvicorn[standard]' pytest httpx
PYTHONPATH=src .venv/bin/python scripts/bootstrap_secrets.py
cd frontend && npm ci && npm run build && cd ..
PYTHONPATH=src .venv/bin/python dev.py
```

打开 <http://127.0.0.1:43123>。

只改界面时，可以另开 `cd frontend && npm run dev`（Vite 把 `/api` 代理到 43123）。

测试：

```bash
PYTHONPATH=src .venv/bin/pytest
```

`scripts/bootstrap_secrets.py` 会在本机生成初始管理员密码，以及 `.dev.vars` 里的 `JWT_SECRET` 和 `ADMIN_PASSWORD_HASH`。这些文件已忽略，不要提交。明文密码不要写进仓库。登录后到「设置 → 修改密码」，然后删掉本机那份初始密码文件。

## 部署

*Deploy*

用 Wrangler / Pywrangler 部署。先构建前端，再上传 Worker。Python 依赖按 `pyproject.toml` 安装，不要只跑不带这些包的 `npx wrangler deploy`。

部署前在 Cloudflare 上设置这两个密钥（只放密钥名，值不要写进 git）：

- `JWT_SECRET`
- `ADMIN_PASSWORD_HASH`

引导管理员邮箱来自配置里的 `ADMIN_EMAIL`。Worker 第一次请求时会自己建表；如果用户表里还没有这封邮箱，会插入引导管理员。已经存在的管理员不会被新的密码哈希覆盖。

D1、R2 的名称和绑定写在 `wrangler.toml`。令牌至少需要 Workers 脚本、D1 和 R2 的编辑权限。
