# MVP 功能开发记录

**项目**：擎天学智 · K12 用户画像推荐系统  
**依据**：`12-全量开发流程文档.md` 阶段 3、`10-接口设计文档.md`、`9-数据库设计文档.md`  
**开始时间**：2026-08-10  
**完成时间**：2026-08-10  
**操作人**：AI Agent（Cursor）

> 记录阶段 3 MVP 开发每一步操作、验证与错误处理。  
> 状态：`OK` / `FAIL` / `WARN` / `SKIP`

---

## 0. 目标与完成判据

对齐阶段 3：画像确认闭环 + 后台三角色 + SSE + Mock 演示。

- [x] 3.A Mock 与数据底座完善  
- [x] 3.B 组织 / 员工 / 权限  
- [x] 3.C 客户 / 订单 / 标签  
- [x] 3.D AI 画像管道闭环  
- [x] 3.E 侧边栏 context + 看板  
- [x] 3.F 侧边栏前端  
- [x] 3.G 管理后台前端  
- [x] 3.H 联调主路径通过  

---

## 1. 操作日志

### 1.1 开工

| 时间 | 步骤 | 操作 | 结果 |
|------|------|------|------|
| 2026-08-10 | 1.1.1 | 创建本记录文件 | OK |
| 2026-08-10 | 1.1.2 | 确认 Compose 仍在运行（api/postgres/nginx） | OK |

### 1.2 后端 · Mock / 底座（3.A）

| 步骤 | 操作 | 结果 |
|------|------|------|
| 3.A.1 | 增强 `POST /mock/seed/demo`：三角色后台账号、客户标签绑定、更多聊天 | OK |
| 3.A.2 | `POST /mock/messages` 支持 `asr_text`；时间 naive UTC | OK |
| 3.A.3 | `POST /mock/orders` 保留 | OK |
| 3.A.4 | `PUT /admin/customers/{id}/cs-summary` | OK |

演示账号：

- `admin` / `admin123`
- `regional` / `regional123`
- `advisor` / `advisor123`

### 1.3 后端 · 组织 / 员工 / 权限（3.B）

| 步骤 | 接口 | 结果 |
|------|------|------|
| 3.B.1 | `CRUD /admin/orgs`（软删） | OK |
| 3.B.2 | `CRUD /admin/users` | OK |
| 3.B.3 | `POST /admin/users/{id}/account` | OK |
| 3.B.4 | 客户/订单/看板查询套 `apply_scope` | OK |
| 3.B.5 | 顾问登录客户列表仅本人（联调可见 SQL `owner_user_id=`） | OK |

### 1.4 后端 · 客户 / 订单 / 标签（3.C）

| 步骤 | 接口 | 结果 |
|------|------|------|
| 3.C.1 | `GET /admin/customers` 筛选分页 | OK |
| 3.C.2 | `GET /admin/customers/{id}` 详情聚合 | OK |
| 3.C.3 | `PATCH /admin/customers/{id}` | OK |
| 3.C.4 | `GET/POST /admin/orders` | OK |
| 3.C.5 | `GET/POST/PATCH /admin/tags` | OK |
| 3.C.6 | `GET /admin/tags/stats` | OK |
| 3.C.7 | `GET/POST/DELETE /sidebar/tags*` | OK |

### 1.5 后端 · 画像管道（3.D）

| 步骤 | 操作 | 结果 |
|------|------|------|
| 3.D.* | `pipeline.py`：ContextLoader → Prompt → Gateway/FakeLLM → Parse（失败重试1次）→ DraftWriter → SSE | OK |
| 3.D.7 | `POST /sidebar/profile/generate` 返回 `job_id`，BackgroundTasks 异步执行 | OK |
| 3.D.8 | `GET /sidebar/profile` confirmed/draft/generating | OK |
| 3.D.9 | `PATCH /sidebar/profile/draft` | OK |
| 3.D.10–11 | `POST /sidebar/profile/confirm` fields/all/discard + event_log | OK |

### 1.6 侧边栏 context + 看板（3.E）

| 步骤 | 接口 | 结果 |
|------|------|------|
| 3.E.1 | `GET /sidebar/context` | OK |
| 3.E.2 | `GET /admin/dashboard/summary`（漏斗简单口径） | OK |

### 1.7 前端（3.F / 3.G）

| 步骤 | 操作 | 结果 |
|------|------|------|
| 3.F | `apps/sidebar`：换票、头区、画像 Tab（生成/确认/忽略）、标签 Tab、SSE 重连；建议/日程灰显 | OK |
| 3.G | `apps/admin`：登录、看板/客户/员工/订单/标签；客户详情含已确认画像 | OK |
| 构建 | `npm run build` 两侧 | OK（sidebar 曾因未用函数 TS 报错，已删） |

### 1.8 联调（3.H）

| 步骤 | 操作 | 结果 |
|------|------|------|
| 3.H.0 | `docker compose down -v && up --build` 空库重建 | OK |
| 3.H.1 | seed → 换票 → generate → 草稿出现 | OK |
| 3.H.2 | confirm all → 后台详情见 confirmed，draft=null | OK |
| 3.H.3 | advisor 登录客户列表 scope 正确 | OK |
| 3.H.4 | 标签列表/stats、看板漏斗 | OK |
| 3.H.5 | Nginx 侧边栏/后台 200 | OK |

---

## 2. 错误与处理

| # | 时间 | 步骤 | 错误现象 | 原因 | 处理 | 结果 |
|---|------|------|----------|------|------|------|
| E1 | 2026-08-10 | sidebar build | `TS6133: 'addTag' is declared but never read` | 预留函数未接入 UI | 删除未用 `addTag` | OK |
| E2 | 2026-08-10 | confirm 联调 | 首次确认返回 `profile_version=2` | 新建 `CustomerProfile` ORM 默认 version=1 后再 +1 | 首次确认（`confirmed_at is None`）置 version=1，其后递增 | OK |
| E3 | 2026-08-10 | 时间展示 | `last_contact_at` 出现 `+00:00Z` 后缀 | naive/aware 序列化拼接了 `Z` | WARN：不阻断；后续可统一 isoformat | WARN |

---

## 3. 验证结果

**阶段 3 MVP 主路径：通过（`MOCK_LLM=true`）。**

验证摘要：

1. Seed 王女士 + 三角色账号 + 标签绑定  
2. 后台客户列表/看板/标签 stats  
3. 侧边栏换票 → context → generate(job_id=1) → draft  
4. confirm all → `draft_status=merged`，后台详情可见 confirmed  
5. advisor scope SQL 过滤 `owner_user_id`  
6. 前端静态资源经 Nginx 可访问  

访问：

| 入口 | URL |
|------|-----|
| 侧边栏 | http://localhost:8080/ |
| 管理后台 | http://localhost:8080/admin/ |
| API Docs | http://localhost:8000/docs |

---

## 4. 产出清单

| 路径 | 说明 |
|------|------|
| `backend/app/features/profile/pipeline.py` | 画像 Pipeline |
| `backend/app/features/profile/router.py` | generate/get/patch/confirm |
| `backend/app/features/admin/router.py` | orgs/users/customers/orders/tags/dashboard |
| `backend/app/features/tag/router.py` | 侧边栏手工标签 |
| `backend/app/features/wecom/context_router.py` | `/sidebar/context` |
| `backend/app/features/mock/router.py` | 增强 seed |
| `apps/sidebar/src/App.vue` | 侧边栏 MVP UI |
| `apps/admin/src/App.vue` | 管理后台 MVP UI |
| `ClassDoc/14-MVP功能开发记录.md` | 本文 |

---

## 5. 已知未做 / 可后续增强（不阻塞 MVP 主路径）

- 组织树前端可视化编辑页较简（API 已有）  
- 订单 CSV 导入、标签侧边栏「从词表添加」UI 未做完整表单  
- SSE 经 Nginx 长连接联调未单独压测（API 直连生成路径已通）  
- `MOCK_LLM=false` + 真实 DeepSeek 冒烟未跑（可选）  
- 时间字段统一 UTC 序列化格式  

下一阶段建议：按 `12` 进入 **阶段 4 MVP 测试 / UAT**，或补前端交互细化。

---

## 修订

| 版本 | 日期 | 说明 |
|------|------|------|
| V0.1 | 2026-08-10 | 起稿，开始 MVP 开发 |
| V1.0 | 2026-08-10 | MVP 主路径联调通过；错误 E1～E3 归档 |
