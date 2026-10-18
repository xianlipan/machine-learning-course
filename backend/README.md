# 北京房价挑战后端

课程站继续由 GitHub Pages 托管；本服务独立部署，仅提供健康检查、排行榜和 CSV 评测 API。不会托管 `data/`，不会返回真实标签或逐样本误差。

## 本地运行（在仓库根目录，PowerShell）

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r backend/requirements.txt mkdocs-material
```

教师手工将 `04_北京房价_测试集标签_教师保留.csv` 放到 `backend/data/`。该目录在 Git 中只保留 `.gitkeep`。也可通过环境变量 `CHALLENGE_LABELS_PATH` 指向仓库外的文件，避免本地复制。标签必须是 UTF-8 CSV，恰好两列 `sample_id,totalPrice`，ID 唯一且目标为有限数字。首次部署缺少标签时服务仍会启动，但禁止评测；上传标签后重启服务才会开放评测。标签存在但格式错误或无法读取时，服务会启动失败，防止错误评分。

```powershell
.venv\Scripts\python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001
```

另开一个终端启动网站：

```powershell
.venv\Scripts\python -m mkdocs serve
```

本地预览时 `docs/javascripts/challenge-config.js` 会自动连接 `http://127.0.0.1:8001`。浏览 `http://127.0.0.1:8000/machine-learning-course/challenge/`（MkDocs 根据现有 site_url 使用此路径前缀）。该文件是前端 API 地址的唯一配置处，正式部署时将占位域名换成后端 HTTPS 域名，不要加 `/api`。

## API 协议

- `GET /api/health`：服务正常返回 HTTP 200 和 `{"status":"ok","evaluation_ready":true}`；首次部署缺少标签时 `evaluation_ready` 为 `false`，表示服务运行中但还未开放评测。
- `GET /api/leaderboard`：返回 `{"leaderboard":[{"entry_id":1,"rank":1,"name":"张三","rmse":52.37}]}`，最多 10 人，不含学号。`entry_id` 是数据库内部行标识，用于在当前页面高亮本次提交对应的条目，同名学生不会混淆。评测成功时也返回该标识。
- `POST /api/evaluate`：`multipart/form-data`，恰好三个字段 `name`、`student_id`、`file`。file 必须是 CSV（最多 10 MiB），恰好两列 `sample_id,prediction`，允许列顺序变化，ID 必须与全部测试 ID 一致且不重复。只支持 UTF-8（可带 BOM）。

成功返回 `success,name,student_id,rmse,best_rmse,rank,total_students,submission_count,remaining_submissions,submitted_at`。`rmse` 是本次成绩，`rank` 按历史最好成绩计算；同分使用竞赛排名（1、1、3）。`submission_count` 是该学号的成功提交次数，`remaining_submissions` 是综合姓名和学号后剩余的可提交次数。提交时间为带时区的 UTC ISO 字符串，浏览器按本地时区显示。失败返回 HTTP 400/413/415 和中文 `detail`；缺少标签时返回 HTTP 503，不评分、不记录提交。无效提交不计次数。任一姓名或学号累计成功提交达到三次后，后续提交返回 HTTP 429，不更新成绩、不增加次数。

提交上限由 SQLite 的独立姓名、学号计数表保存；每次成功提交分别累加，修改姓名或更换学号不会清除原身份计数。上限检查和计数更新在同一写事务内完成，避免并发突破三次限制。首次升级会从已有排行榜迁移学号次数，并按当前存储姓名汇总历史次数；旧系统没有保存的历史曾用姓名无法追溯。升级、重启不清空排行榜或提交计数。

SQLite 使用事务按 student_id 原子更新。更差成绩保留 best_rmse，但次数仍加一；姓名和 updated_at 更新到最近一次有效提交。默认数据库 `backend/leaderboard.db`。支持用 `CHALLENGE_DB_PATH` 配置持久磁盘路径。数据库、日志和标签不应放入静态托管目录。

## 部署独立后端

1. 在支持 Python 3.12 的服务器上检出仓库，建立虚拟环境并安装 `backend/requirements.txt`。
2. 通过私密传输手工放入标签，或配置 `CHALLENGE_LABELS_PATH` 指向私密目录。禁止提交标签到 Git。
3. 将数据库配置到持久磁盘，给服务用户读标签、写数据库的权限；备份数据库，避免临时容器重启后丢榜。
4. 设置 `CHALLENGE_ALLOWED_ORIGINS=https://xianlipan.github.io`。多个来源用逗号分隔，填 origin 而非带路径的网址。默认同时允许上述正式站和两个本地开发地址。
5. 以服务管理器运行 `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8001`，通过 Nginx/Caddy 等反向代理提供 HTTPS。只代理 FastAPI，不挂载 `backend/data/`。代理请求体上限设为 11 MB（给 multipart 留开销），配置合理超时。
6. 验证 HTTPS `/api/health`，修改 `challenge-config.js` 为正式后端地址，再提交网站改动。GitHub Actions 继续构建原 MkDocs 站点；Pages 不会运行 Python 后端。

CORS 遵循 [FastAPI 官方文档](https://fastapi.tiangolo.com/tutorial/cors/)。本服务没有身份认证，姓名和学号由学生填写，不能防止冒用；CSV 结果也无法证明学生实际使用的模型或训练方法，需结合课程实验材料检查。每个姓名或学号最多成功提交三次，不返回逐样本结果。同名学生共享姓名额度，符合按姓名或学号任一项限制的规则。

## 验证

### Render 首次部署

保持 Root Directory 为空，Language 选择 Python 3，Build Command 为 `pip install -r backend/requirements.txt`，Start Command 为 `uvicorn backend.app:app --host 0.0.0.0 --port $PORT`，Health Check Path 为 `/api/health`。

挂载 1 GB 持久磁盘到 `/var/data`，设置：

```text
CHALLENGE_LABELS_PATH=/var/data/labels.csv
CHALLENGE_DB_PATH=/var/data/leaderboard.db
CHALLENGE_ALLOWED_ORIGINS=https://xianlipan.github.io
```

1. 推送代码后创建服务。首次启动没有标签是正常情况，`/api/health` 返回 `evaluation_ready:false`。排行榜正常可读，提交评测返回中文“尚未配置”提示。
2. 服务首次部署成功后，通过 Render 的 SSH/SCP 私密上传教师标签到 `/var/data/labels.csv`。使用控制台 Connect 提供的实际 SSH 主机和用户名。不要将标签放入 Git、公开下载地址或构建日志中。
3. 上传完成后在控制台重启服务，确认 `/api/health` 的 `evaluation_ready` 变成 `true`。以后更新标签也需要重启。
4. 将 `docs/javascripts/challenge-config.js` 中的正式后端占位域名换成 Render 提供的 HTTPS 地址，提交并推送网站更新。
5. 修改页面或重启后端不会清空 `/var/data/leaderboard.db`。不要删除磁盘或把数据库改到临时目录；定期备份数据库。

### 自动检查

```powershell
.venv\Scripts\python -m pip install pytest httpx
.venv\Scripts\python -m pytest backend/tests -q
.venv\Scripts\python -m mkdocs build --strict
```

提交前检查 `git check-ignore backend/data/04_北京房价_测试集标签_教师保留.csv backend/leaderboard.db`，并确认 `git ls-files` 没有教师标签。不要用 `git add -f` 绕过忽略规则。
