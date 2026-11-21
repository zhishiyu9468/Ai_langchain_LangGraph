# Chatbot 部署文档

## 项目简介

前后端分离的 AI 对话机器人，支持用户注册登录、会话历史管理、流式对话。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.12, FastAPI, pymysql |
| 数据库 | MySQL 8.0 |
| 前端 | HTML + JS + CSS, Nginx |
| AI 模型 | DeepSeek V4 Flash |
| 部署 | Docker Compose |

## 环境要求

- Docker 20.10+
- Docker Compose 2.0+
- （本地开发）Python 3.10+、uv、MySQL 8.0

## 快速部署（Docker）

### 1. 配置环境变量

编辑项目根目录的 `.env`，填入你的 DeepSeek API Key：

```env
DEEPSEEK_API_KEY=sk-your-actual-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
MYSQL_HOST=mysql
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=MySQL123
MYSQL_DB=robot
JWT_SECRET=生成一个随机字符串
```

> **JWT_SECRET 务必修改**，可以用 `openssl rand -hex 32` 生成。

### 2. 启动服务

```bash
docker-compose up -d --build
```

### 3. 访问

浏览器打开 `http://localhost`。

## 服务端口

| 服务 | 端口 | 说明 |
|---|---|---|
| frontend | 80 | Nginx 静态服务 + API 代理 |
| backend | 8000 | FastAPI 后端 |
| mysql | 3306 | MySQL 数据库 |

## 本地开发

### 后端

```bash
# 1. 进入后端目录
cd backend

# 2. 安装依赖
uv sync

# 3. 修改 .env 中的 MYSQL_HOST 为 localhost
# MYSQL_HOST=localhost

# 4. 确保 MySQL 已运行且 robot 库已创建
mysql -u root -pMySQL123 -e "CREATE DATABASE IF NOT EXISTS robot"

# 5. 启动后端
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

API 文档: `http://localhost:8000/docs`

### 前端

直接用浏览器打开 `frontend/public/login.html` 即可（前提是后端已在 8000 端口运行）。生产环境由 Nginx 统一代理。

## 项目结构

```
.
├── .env                          # Docker 环境变量
├── docker-compose.yml
├── backend/
│   ├── .env / .env.example       # 本地开发 / 模板
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── src/
│       ├── main.py               # FastAPI 入口
│       ├── config.py             # 配置
│       ├── database.py           # MySQL 连接 + 建表
│       ├── auth.py               # JWT + bcrypt
│       ├── deepseek.py           # DeepSeek SSE 调用
│       └── routers/
│           ├── auth.py           # 注册/登录
│           ├── chat.py           # SSE 流式对话
│           └── conversation.py   # 会话 CRUD
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    └── public/
        ├── login.html
        ├── register.html
        ├── index.html
        ├── css/style.css
        └── js/
            ├── api.js
            └── chat.js
```

## 常用操作

### 查看日志

```bash
docker-compose logs -f backend
```

### 重启服务

```bash
docker-compose restart backend
```

### 停止服务

```bash
docker-compose down
```

### 清理数据（含数据库）

```bash
docker-compose down -v
```

## FAQ

**Q: 注册时提示密码太长？**
密码已做截断处理，正常情况不会遇到此问题。

**Q: 前端打开后白屏？**
检查 Nginx 是否正确代理到后端，确认 `docker-compose` 三个服务都处于 `Up` 状态。

**Q: DeepSeek API 调用失败？**
确认 `.env` 中 `DEEPSEEK_API_KEY` 有效且 `DEEPSEEK_BASE_URL` 可访问。

**Q: `uv sync` 报编译错误？**
本项目所有依赖均为纯 Python，不涉及 C 编译。如遇到 `greenlet` 编译错误，请删除 `uv.lock` 后重试：
```bash
rm -f uv.lock && uv sync
```
