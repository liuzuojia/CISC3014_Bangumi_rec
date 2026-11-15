# Deploy · 部署清单（Render / PythonAnywhere）

这个文件夹是**可以直接部署的最小版本**：只保留运行所需的文件（1.5 MB）。

This folder is the minimal deployable copy: only what the app needs at runtime (1.5 MB).

```
deploy/
├── app.py              Flask 应用（读取 data/ 下的 5 个文件）
├── requirements.txt    flask, numpy, gunicorn（Linux）
├── render.yaml         Render Blueprint
├── Procfile            gunicorn app:app
├── .gitignore
└── data/
    ├── items.json      912 条条目
    ├── tag_matrix.npz  912 × 2000 标签矩阵
    ├── vocab.json      标签词表
    ├── tags.json       界面用的 120 个标签
    └── stats.json      页头统计数字
```

## 本地自测 · test locally

```bash
pip install -r requirements.txt
python app.py --host 127.0.0.1 --port 5000
# open http://127.0.0.1:5000/?lang=en
```

## 部署方式一：GitHub 网页上传 + Render（不用装 Git）

1. 打开 https://github.com/new ，仓库名 `bangumi-recommender`，选 **Public**，创建。
2. 在空仓库页面点 **uploading an existing file**。
3. 把本文件夹里的**全部内容**（`app.py`、`requirements.txt`、`render.yaml`、`Procfile`、`data` 文件夹）拖进浏览器，点 **Commit changes**。
4. 打开 https://dashboard.render.com/ → **New +** → **Blueprint** → 选择该仓库 → **Apply**。
5. 等待 2–4 分钟构建完成，得到 `https://bangumi-recommender.onrender.com`。
6. 首次打开可能需要 30–60 秒（免费实例会休眠）。

## 部署方式二：命令行（推荐长期使用）

```powershell
winget install --id Git.Git -e
# 重新打开终端，让 PATH 生效
cd D:\UM\CISC3014\bangumi_rec\deploy
git init
git add .
git commit -m "Bangumi recommender: deployable app"
git branch -M main
git remote add origin https://github.com/<你的用户名>/bangumi-recommender.git
git push -u origin main
```

之后每次改动：`git add . && git commit -m "update" && git push`，Render 会自动重新部署。

## 部署方式三：PythonAnywhere（完全不碰 Git）

1. 注册 https://www.pythonanywhere.com/ （免费版即可）。
2. **Files** → 新建目录 `bangumi_rec`，进入后用 **Upload a file** 依次上传
   `app.py`、`requirements.txt`；再新建目录 `data`，上传 `data/` 里的 5 个文件。
3. 打开 **Bash console**，执行：
   ```bash
   cd ~/bangumi_rec
   pip install --user flask numpy
   ```
4. **Web** → **Add a new web app** → **Flask** → Python 3.10 → 记住 WSGI 配置路径。
5. 点开该 WSGI 文件，用本目录的 `pythonanywhere_wsgi.py` 内容替换（改掉用户名）。
6. **Reload** → 访问 `https://<你的用户名>.pythonanywhere.com/?lang=en`。

## 部署后自检 · post-deploy checks

| 检查 · Check | 期望 · Expected |
|---|---|
| 首页 | 200，显示 912 条目 / 137 当季 |
| `/?lang=en` | 英文界面 |
| `/api/recommend?tags=异世界&kind=anime&airing=1&n=5` | JSON，5 条结果 |
| Render Logs | `Booting worker with pid ...` 且无 traceback |

## 常见问题 · troubleshooting

| 现象 · Symptom | 原因 · Cause | 处理 · Fix |
|---|---|---|
| Build failed: `No module named flask` | 没有 requirements.txt 或路径不对 | 确认仓库根目录有 `requirements.txt` |
| `gunicorn: command not found` | Linux 环境没装 gunicorn | requirements 里已含（`sys_platform != "win32"`） |
| 502 / 503 | 应用启动失败 | 看 Logs，多半是 `data/` 缺失或文件名大小写不一致 |
| 第一次打开很慢 | 免费实例休眠 | 正常，再等 30 s；可用 UptimeRobot 定时 ping |
| 页面能开但没有数据 | `data/` 没上传 | 确认 5 个文件都在 `data/` 下 |
| 中文乱码 | 文件编码不是 UTF-8 | 用 UTF-8 重新上传 |

## 成本 · cost

Render Free：750 小时/月、512 MB 内存、自动休眠；本项目内存占用约 120 MB，完全够用。
PythonAnywhere Free：512 MB 磁盘、每天 CPU 秒数有限，演示足够。
