# personal-pm-web

个人项目管理系统的 Web 版。用浏览器登录后管理项目、任务、费用和附件，数据按工作区隔开，多名用户可以共用同一个工作区。

本仓库是 [personal-pm](https://github.com/leonjianghao1900/personal-pm) 的姊妹项目。那边是本地版（Python FastAPI + Vue 3，数据在本机 SQLite）。这边把同一类使用方式放到 Cloudflare 上，用 D1 和 R2 代替本地数据库和本地文件，并加上账号与多工作区。两个仓库各自维护。

这个 GitHub 仓库是镜像。源码以 Cursor Origin 上的 `leondoubao/personal-pm-web` 为准，那边可能有尚未同步过来的修复。下文描述的是本仓库 `main` 上的代码。

文中的邮箱、密钥和 Cloudflare 标识一律用占位符。真实的 `account_id`、`database_id`、邮箱和密钥只放在本机或 Cloudflare 上，不要写进公开说明。

## 项目目的

给个人或小团队一个打开浏览器就能用的项目管理站点：

- 管理员创建工作区、创建用户，并把用户放进某个工作区。
- 同一工作区里的人看到同一份项目、任务、费用、收件箱和附件。
- 别的工作区的记录按不存在处理（接口返回 404）。
- 可以导出当前工作区的备份，也可以把 [personal-pm](https://github.com/leonjianghao1900/personal-pm) 备份版本 1–3 恢复进一个工作区。

没有公开注册。账号由管理员创建，或由首次请求时插入的引导管理员开始。

## 技术栈

版本以仓库配置为准。Python 依赖没有 `uv.lock`，只有下界。前端精确版本来自 `frontend/package-lock.json`。

| 部分 | 配置 |
| --- | --- |
| 运行时 | Cloudflare Workers，`compatibility_date = 2026-11-05`，`compatibility_flags = ["python_workers"]`（Python Workers / Pyodide）。Pyodide 版本由平台决定，仓库没有钉死 |
| 应用 | FastAPI `>=0.115`，由 `workers` ASGI 入口挂上 Worker（`src/worker.py`）。应用版本 `0.1.0` |
| 数据 | D1，绑定名 `DB`。本地 `dev.py` 用 SQLite 文件 `data/pm.sqlite`，SQL 与线上相同 |
| 附件 | R2，绑定名 `ATTACHMENTS`。本地用目录 `data/blobs/` |
| 静态资源 | Workers Assets，绑定名 `ASSETS`，目录 `frontend/dist`。`not_found_handling = single-page-application`，`run_worker_first = true`（`/api` 优先于前端构建结果） |
| 前端 | Vue 3.5.41、Vue Router 4.6.4、Pinia 2.3.1、Vite 5.4.21、TypeScript 5.9.3、Tailwind CSS 3.4.19、Axios 1.19.0、date-fns 3.6.0。`package.json` 里是兼容范围，上表是锁文件里的版本 |
| Python 工具 | `uv`（`pyproject.toml` 有 `[tool.uv]`，`package = false`）。仓库没有钉 uv 自身的版本 |
| Worker 工具 | `pywrangler`，来自依赖组 `dev` 里的 `workers-py` / `workers-runtime-sdk`（版本未钉死）。部署和 D1 迁移用它，这样才会带上 `pyproject.toml` 里的 Python 依赖 |
| 前端工具 | npm、`vue-tsc` 2.2.12、Vite。构建脚本是 `vue-tsc && vite build` |
| 其他 Python 库 | Pydantic `>=2.6`、python-multipart `>=0.0.9`、openpyxl `>=3.1`。本地服务和测试另有 uvicorn `>=0.32`、pytest `>=8.0`、httpx `>=0.27` |
| 语言版本 | Python `>=3.12`。前端锁的是 Vite 5.4，需要 Node.js 18 或更高；`package.json` 没有 `engines` 字段 |

绑定名称、数据库名和存储桶名写在 `wrangler.toml` 的 `[[d1_databases]]` 与 `[[r2_buckets]]`。下面的命令用 `<database_name>` 表示该文件里的 `database_name`。

## 安装和本地开发

```bash
uv sync --group dev
cd frontend && npm ci && npm run build && cd ..
uv run python dev.py
```

然后打开 <http://127.0.0.1:43123>。

`dev.py` 会：

1. 调用 `scripts/bootstrap_secrets.py` 同一套逻辑，在本机生成尚未存在的密钥文件。
2. 读取 `.dev.vars`（已在 `.gitignore` 中）。
3. 使用 `data/pm.sqlite` 和 `data/blobs/`。
4. 在 `0.0.0.0` 上监听。端口读环境变量 `PORT`，默认 `43123`。
5. 若 `frontend/dist/index.html` 存在，由这个进程提供页面；否则页面请求会提示先构建前端。`/api` 仍然可用。

只改界面时另开一个终端：

```bash
cd frontend && npm run dev
```

Vite 开发服务器在 <http://127.0.0.1:5173>，把 `/api` 代理到 `127.0.0.1:43123`。请先让 `dev.py` 跑着。

本地第一次请求会执行内嵌的 `CREATE TABLE IF NOT EXISTS`（`src/app/bootstrap.py`），因此 **本地 SQLite 不需要** 再跑 Wrangler 的 D1 迁移。新建的 **Cloudflare D1** 必须手动迁移，见下文。

引导文件（都已忽略，不要提交）：

| 文件 | 内容 |
| --- | --- |
| `artifacts/ADMIN_INITIAL_PASSWORD.txt` | 明文初始密码。登录后到「设置」修改，然后删除这个文件 |
| `artifacts/ADMIN_PASSWORD_HASH.txt` | 对应的 PBKDF2 哈希，可用来填写线上的 `ADMIN_PASSWORD_HASH` |
| `artifacts/JWT_SECRET.txt` | 本地 JWT 签名密钥 |
| `.dev.vars` | `JWT_SECRET`、`ADMIN_PASSWORD_HASH`、`ADMIN_EMAIL` |

`ADMIN_EMAIL` 决定引导管理员的邮箱。线上改 `wrangler.toml` 的 `[vars]`，本地改 `.dev.vars`。示例：`admin@example.com`。

测试：

```bash
uv run pytest
```

`pyproject.toml` 已把 `src` 放进 pytest 的 `pythonpath`。

## 部署

先构建前端，再用 pywrangler 发布。pywrangler 会读取 `[dependency-groups].dev` 并打包 Worker 需要的 Python 依赖。

```bash
cd frontend && npm ci && npm run build && cd ..
uv run pywrangler deploy
```

`wrangler.toml` 里 `workers_dev = true`。部署完成后的地址在 Cloudflare 控制台查看，本文不写具体子域名。

发布前要先准备好 Secrets、`ADMIN_EMAIL`，并对 **新建的 D1 执行迁移**。

### D1 迁移

**新建的 D1 数据库必须手动执行迁移。** 只在控制台建库，或只在 `wrangler.toml` 里写上绑定，表不会进入 Wrangler 的迁移记录。每个新建的库都要执行一次：

```bash
uv run pywrangler d1 migrations apply <database_name> --remote
```

`<database_name>` 用 `wrangler.toml` 里 `[[d1_databases]]` 的 `database_name`，不要把 `database_id` 或 `account_id` 抄进文档。

给 Wrangler 本地 D1 建表时用：

```bash
uv run pywrangler d1 migrations apply <database_name> --local
```

当前迁移目录是 `migrations/`，只有 `migrations/0001_init.sql`。它和 `src/app/schema.py` 里的 `SCHEMA_SQL` 保持一致，`tests/test_schema.py` 会核对两边相同。表包括工作区、用户、项目、任务、任务依赖、费用类别、费用、收件箱和附件元数据。

当前这份代码在进程内第一次请求时，还会执行同一份 `CREATE TABLE IF NOT EXISTS`，并写入应用自己的 `schema_migrations` 版本号。这只补齐缺表，**不代替**上面的手动迁移，也不会登记 Wrangler 的迁移版本。新建库请先执行 `migrations apply`，再部署或访问。

`dev.py` 使用的本地 SQLite 由这次启动时的建表逻辑负责，不必对那个文件执行 `d1 migrations apply`。

### Secrets 和变量

只列名称和用途。值用 `secret put` 或 `[vars]` 配置，不要写进 git。

| 名称 | 放在哪里 | 用途 |
| --- | --- | --- |
| `JWT_SECRET` | Secret | HS256 会话令牌的签名密钥。短于 16 个字符时，登录和需要登录的接口返回 500，提示未配置 |
| `ADMIN_PASSWORD_HASH` | Secret | 引导管理员密码的 PBKDF2-HMAC-SHA256 哈希，格式为 `pbkdf2_sha256$<迭代次数>$<盐十六进制>$<摘要十六进制>`。迭代次数是 100000。仅当用户表里还没有 `ADMIN_EMAIL` 时插入该管理员；已存在的账号不会被新哈希覆盖 |
| `ADMIN_EMAIL` | `[vars]`，不是 Secret | 引导管理员邮箱，写入前会转成小写。示例：`admin@example.com`。请改成你自己的地址 |
| `PORT` | 仅本地进程环境变量 | `dev.py` 的监听端口，默认 `43123`。Worker 不读它 |

设置 Secret：

```bash
uv run pywrangler secret put JWT_SECRET
uv run pywrangler secret put ADMIN_PASSWORD_HASH
```

命令会提示输入，输入内容不要出现在 shell 历史或仓库里。哈希可以用本地 `artifacts/ADMIN_PASSWORD_HASH.txt` 的内容。

资源绑定（名称在 `wrangler.toml`，不是 Secret）：

| 绑定 | 类型 | 用途 |
| --- | --- | --- |
| `DB` | D1 | 全部业务表 |
| `ATTACHMENTS` | R2 | 附件对象，键为 `ws/<工作区 id>/<库里保存的相对路径>` |
| `ASSETS` | Assets | `frontend/dist` 静态资源 |

发布用的 API 令牌需要能编辑这个 Worker、对应的 D1 和 R2。令牌本身不要写入仓库。

Worker 第一次请求时，若用户表还没有 `ADMIN_EMAIL`，会插入一名显示名为「管理员」的管理员，`must_rotate_password = 1`，且尚未加入工作区。插入失败后若该邮箱已存在，则保持原记录。

## 使用说明

以下功能都在当前路由和视图里核对过。接口形状也可以看 `/api/docs`（OpenAPI）和 `/api/openapi.json`。健康检查是 `GET /api/health`，版本是 `GET /api/version`。

会话放在名为 `pm_session` 的 Cookie 里：HttpOnly、`SameSite=Lax`、路径 `/`、有效期 7 天。请求是 HTTPS 时带 `Secure`。退出登录会清掉这个 Cookie。

未登录访问业务页会去 `/login`，并带上 `next`。已登录用户再打开 `/login` 会进自己的首页：有工作区去总览；管理员但没有工作区去工作区管理；普通用户没有工作区去「等待分配」。

顶栏可以切换当前项目、退出，以及浅色/深色（记在本机 `localStorage` 的 `pm-theme`）。没有工作区时，侧栏只留下该角色能用的管理入口。

### 登录

打开 `/login`，用邮箱和密码登录。没有自助注册，也没有找回密码或邮箱验证。

登录后若横幅提示这是初始密码，到 `/settings` 修改。新密码至少 10 位，且不能与当前密码相同。管理员创建用户时设置的也是初始密码，用户记录上会标记待修改。

### 工作区

一名用户同时只属于一个工作区。管理员可以暂时不分配工作区；普通用户必须有工作区，否则创建或改成普通用户时会被拒绝。

管理员在 `/admin/workspaces`：

- 创建、改名工作区。
- 查看成员数。
- 点「设为我的工作区」，把自己放进该工作区。
- 删除工作区。仍有成员时会拒绝，需要先把成员调走。删除会去掉该工作区的业务数据和对应附件对象。

尚无工作区的普通用户只能看到 `/awaiting`，需要管理员分配之后才能使用项目、任务和费用。

同一工作区的用户看到同一份数据。查询、修改、删除和下载附件都带当前用户的 `workspace_id`；其他工作区的 id 返回 404。

### 项目和任务

有工作区的用户可以使用这些页面：

| 路径 | 页面 |
| --- | --- |
| `/` | 重定向到 `/dashboard` |
| `/dashboard` | 总览：项目数、进行中任务、状态为延期的任务数、本月支出、月历、各项目进度、近 12 个月费用条 |
| `/tasks` | 项目列表。新建、编辑（名称、颜色、起止日期、备注）、删除、打开甘特图、导出 Excel。删除项目会级联删除其任务 |
| `/gantt` | 当前项目的任务列表，以及月 / 周 / 日三种日历。可新建项目、新建任务（名称和起止日期）、打开任务详情、导出 Excel |
| `/gantt/<项目 id>/task/<任务 id>` | 任务详情 |

任务详情可以改名称、状态、优先级、进度（0–100，步进 5）、起止日期、描述、是否里程碑，也可以标记完成、把进度重置为 0、删除任务，以及管理该任务的附件。

状态：未开始 `todo`、进行中 `progress`、已延期 `delayed`、已完成 `done`、已取消 `cancelled`。优先级：低、普通、高、紧急。总览月历和甘特图的月视图会跳过已取消的任务。周视图和日视图仍会画出带日期的已取消任务。

Excel 从项目列表、甘特图和费用页导出当前项目，接口是 `GET /api/projects/<id>/export`。工作簿有四张表：项目概览、任务清单、费用记录、甘特图。甘特图用单元格按状态填色；跨度超过 90 天时按周着色。

### 费用

`/costs` 记录支出：名称、金额（大于 0）、日期、类别、可选说明、所属项目、可选关联任务。可以改名、编辑、删除，并按项目筛选。

总支出、笔数、本月合计和类别占比来自 `GET /api/stats/costs`（可按项目过滤）。单笔最高取当前列表里的最大金额。趋势图按月、周、日切换，由页面根据已经加载的费用自行汇总。

费用类别在 `/settings` 里管理，费用页有入口。新建工作区时会写入四条内置类别：材料、人工、差旅、其他。类别可改名、改颜色；名称在工作区内唯一。已被费用使用的类别不能删除。改名会同步更新已有费用上的类别文本。

费用也可以带附件，每笔最多 5 个。

### 附件

任务、费用、收件箱可以上传文件。单文件上限 20 MB。数量上限：任务 10 个，费用 5 个，收件箱 5 个。

对象存在 R2（本地则在 `data/blobs/`）。数据库只存相对路径。下载地址是 `GET /api/attachments/<id>/download`，并且只对当前工作区有效。删除任务、费用、收件箱条目或项目时，会一并删掉对应附件记录和对象。

### 备份

有工作区的用户在 `/settings` 可以：

- 下载 JSON 备份（不含附件文件本体）。
- 下载完整 ZIP（`backup.json` 加上附件字节）。
- 选择 `.json` 或 `.zip` 恢复。恢复前有确认框，成功后页面会重新加载。

备份和恢复只替换 **当前工作区** 的项目、任务、任务依赖、费用、费用类别、收件箱和附件。用户表和工作区本身不在备份里。恢复时会重写这些表的 id，避免和别的工作区撞号。

支持的备份版本是 1、2、3，与 personal-pm 的导出兼容。JSON 上限 50 MB，ZIP 上限 100 MB，解压后上限 120 MB。

这些接口的路径在 `/api/admin/backup`、`/api/admin/backup/full`、`/api/admin/restore`、`/api/admin/restore/full`。当前代码要求调用者已登录且已加入工作区，并不额外要求管理员角色。因此同一工作区里的普通用户也能下载和覆盖本工作区数据。

JSON 恢复会写回附件的元数据，但不会上传文件字节。完整 ZIP 恢复会按包内文件写回对象。恢复结束后，不再属于这份备份的旧附件对象会被删除。

### 管理员

`/admin/users` 仅管理员可进：

- 创建用户：邮箱、显示名（可空，空则用邮箱本地部分）、初始密码（至少 10 位）、角色（管理员或普通用户）、工作区（管理员可以不分配）。
- 修改角色、工作区，或重置密码。重置后该用户再次被标记为需要修改密码。
- 删除用户。不能删除当前登录账号，也不能删除最后一名管理员。把最后一名管理员改成普通用户同样会被拒绝。邮箱不能重复。

### 收件箱

`/inbox` 用来随手记录两类条目：

- 插队：可填提醒时间，可标记完成或归档。
- 点子：活跃时可「转正为任务」。选择目标项目后生成一条任务，该收件箱条目改为已归档，并记下新任务 id。

条目有标题、备注、优先级。编辑时可以管理附件；新建时选中的文件会在保存后上传。列表分成「活跃」和「已归档」。

## 当前能力与已知限制

对照 `main` 上的路由、视图和迁移代码，当前实际能力与缺口如下。

**已经提供**

- 邮箱密码登录、修改密码、退出。密码以 PBKDF2-HMAC-SHA256 保存。Workers 上用 WebCrypto，迭代次数 100000（该平台的上限）；本地 CPython 可以用 `hashlib.pbkdf2_hmac`。
- 管理员 / 普通用户两种角色，多工作区，工作区内数据共享，跨工作区访问返回 404。
- 项目、任务、里程碑、进度、优先级、状态、月历和周/日时间条、Excel 导出。
- 费用、费用类别、收件箱（插队与点子、完成、归档、点子转正）。
- 任务、费用、收件箱附件。
- 当前工作区的 JSON 备份与含附件的 ZIP 备份，以及版本 1–3 的恢复。
- 深色模式、OpenAPI 文档、`/api/health`。

**限制（代码里没有，或有接口但界面没用上）**

- 没有自助注册、找回密码、邮箱验证、多因素认证，也没有刷新令牌。会话过期后需要重新登录。
- 一人一个工作区，不能同时加入多个。界面没有「切换到另一个工作区」的普通用户入口；管理员把自己改到另一个工作区，用的是用户更新接口。
- 新建 D1 后必须手动执行迁移。首次请求里的 `CREATE TABLE IF NOT EXISTS` 只是同一份建表 SQL 的补齐，不更新 Wrangler 迁移记录。
- 引导管理员一旦插入，再改 `ADMIN_PASSWORD_HASH` 不会覆盖他的密码。忘记密码时由另一名管理员重置，或自行在「设置」里修改。
- 甘特图不能拖拽改期。`POST /api/tasks/<id>/move` 存在，当前视图没有调用它。
- 任务表有 `parent_id`，甘特列表会按父子缩进，接口也能创建子任务并拒绝成环。新建任务对话框不填写父任务，任务详情里也不能添加子任务。
- 任务依赖表和接口支持 `FS`、`SS`、`FF`、`SF`，并会拒绝环。`frontend/src/stores/tasks.ts` 能列出和添加依赖，但没有任何视图调用，甘特图也不画依赖线。
- 项目状态在接口里可以是 `active` 或 `archived`。项目编辑面板没有归档开关。
- 费用金额在界面上固定显示为人民币符号，没有多币种。
- Excel 按钮的提示文字写着甘特图 PNG。导出实现用单元格填色，因为 Python Workers 里没有 Pillow。
- `frontend/src/components/UpdateBanner.vue` 和 `updatesApi` 会请求 `/api/updates/check`，但后端没有这条路由，组件也没有挂到 `App.vue`，界面不会提示新版本。
- `frontend/vite.config.ts` 把 `/ws` 代理到 `127.0.0.1:8765`。本仓库没有 WebSocket 服务，页面也不连接它。
- 备份接口挂在 `/api/admin` 下，授权却是「已加入工作区的用户」。普通成员可以恢复并覆盖本工作区。JSON 恢复不带回附件文件。
- 删除仍有成员的工作区会被拒绝。不能删除自己或最后一名管理员。
- `GET /api/version` 的 `build_time` 在代码里写死为 `2026-11-05`，不会随每次构建变化。
- Python 依赖没有锁文件。`workers-py` 与 `workers-runtime-sdk` 未写版本号，换环境时解析结果可能不同。
