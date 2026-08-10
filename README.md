# K12-UserProfile

擎天学智 · K12 用户画像推荐系统（智能销售辅助）

技术栈：Vue 3 + TypeScript（侧边栏 / 管理后台）+ FastAPI 单体 + PostgreSQL + SSE + DeepSeek。

## 快速启动（脚手架）

```bash
# 1) 配置环境
cp .env.example .env

# 2) 构建前端静态资源（供 Nginx 挂载）
cd apps/sidebar && npm install && npm run build && cd ../..
cd apps/admin && npm install && npm run build && cd ../..

# 3) 一键起环境
cd deploy
docker compose up --build -d
```

访问：

| 入口 | URL |
|------|-----|
| 侧边栏壳 | http://localhost:8080/ |
| 管理后台壳 | http://localhost:8080/admin/ |
| API 文档 | http://localhost:8000/docs |
| Health | http://localhost:8000/health |

首次种子数据：

```bash
curl -X POST http://localhost:8000/api/v1/mock/seed/demo
```

默认后台账号：`admin` / `admin123`（见 `.env` 的 `SEED_ADMIN_*`）。

## 目录

```text
apps/sidebar          # 企微侧边栏 H5
apps/admin            # 管理后台
backend/              # FastAPI 单体
deploy/               # docker-compose + nginx
ClassDoc/             # 需求/设计/流程文档
docs/                 # 指向 ClassDoc
```

脚手架搭建过程与错误记录见：`ClassDoc/13-工程脚手架搭建记录.md`。
