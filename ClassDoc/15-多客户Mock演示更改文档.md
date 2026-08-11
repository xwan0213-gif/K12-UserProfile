# 多客户 Mock 演示能力更改文档

**项目**：擎天学智 · K12 用户画像推荐系统  
**日期**：2026-08-11  
**范围**：Mock 多客户 / 模拟回复 → 画像生成演示闭环  
**操作人**：AI Agent（Cursor）

---

## 1. 变更目标

支持在不改画像主干流水线的前提下：

1. 创建 / 列出不同客户  
2. 为指定客户写入模拟聊天回复  
3. 一键灌入场景脚本（客户 + 多轮对话）  
4. 侧边栏切换客户并触发画像生成  
5. `MOCK_LLM=true` 时 FakeLLM 也能按 context 产出差异化草稿  

---

## 2. 变更清单

| 类型 | 路径 | 说明 |
|------|------|------|
| 后端 | `backend/app/features/mock/router.py` | 新增客户列表/创建、场景种子；消息接口校验客户存在 |
| 后端 | `backend/app/features/ai/providers/fake.py` | FakeLLM 基于 `context.customer` / `messages` 派生字段 |
| 前端 | `apps/sidebar/src/App.vue` | Mock 面板：切客户、写回复、一键物理场景 |
| 文档 | `ClassDoc/15-多客户Mock演示更改文档.md` | 本文档 |

**未改动**：`profile/pipeline.py`、`profile/router.py` generate/confirm 主路径（已按 `customer_id` 工作）。

---

## 3. 新增 / 调整接口

前缀：`/api/v1`

### 3.1 `GET /mock/customers`

列出未删除客户（默认最多 50）。

响应 `data.items[]`：`id` / `external_id` / `parent_name` / `student_name` / `grade` / `school` / `stage` / `owner_user_id` / `org_id`

### 3.2 `POST /mock/customers`

创建客户。未传 `owner_user_id` / `org_id` 时挂到默认顾问（需已 `seed/demo`）。

请求示例：

```json
{
  "parent_name": "陈女士",
  "student_name": "陈小雨",
  "grade": "初三",
  "school": "实验中学",
  "stage": "junior",
  "external_id": "demo_chen"
}
```

`external_id` 冲突返回 `409`。

### 3.3 `POST /mock/seed/scenario`

按 `external_id` 复用或新建客户，并写入对话（可 `append_messages=false` 覆盖旧聊天）。

请求示例：

```json
{
  "external_id": "demo_physics",
  "parent_name": "赵女士",
  "student_name": "赵一凡",
  "grade": "高一",
  "school": "市一中",
  "stage": "senior",
  "append_messages": false,
  "cs_summary": "关注高一物理一对一，价格敏感。",
  "messages": [
    { "direction": "in", "content": "孩子高一物理跟不上，想问有没有一对一" },
    { "direction": "out", "content": "方便说下最近考试分数吗？" },
    { "direction": "in", "content": "期中物理 58，想先试听，价格别太贵" }
  ]
}
```

返回：`customer_id`、`message_ids`、`created` 等。

### 3.4 `POST /mock/messages`（调整）

- 增加客户存在性校验  
- 成功后更新 `customer.last_contact_at`  

---

## 4. FakeLLM 行为

当 `MOCK_LLM=true`：

- 从 `payload.context.customer` 填 `basic_info`  
- 扫描近窗聊天关键词（数学/物理/化学/英语/语文、试听、价格等）填 `study_info` / `prefer_info`  
- 不同客户 / 不同回复会得到不同草稿（仍为规则派生，非真实推理）  

当 `MOCK_LLM=false`（当前 Compose 默认）：仍走 DeepSeek，context 由 pipeline 注入。

---

## 5. 侧边栏使用方式

1. 打开侧边栏（需已 `POST /mock/seed/demo`）  
2. **Mock 演示**面板：  
   - 下拉切换客户，或改 `external_userid` 后「重新换票」  
   - 输入模拟回复 →「写入回复」  
   - 「一键物理场景」创建/刷新 `demo_physics`  
3. 点击「生成画像」→ 等待 SSE `profile_draft` / 刷新草稿  
4. 确认或忽略草稿  

---

## 6. 推荐联调步骤（curl）

```bash
# 1) 确保底座
curl -X POST http://localhost:18000/api/v1/mock/seed/demo

# 2) 场景客户
curl -X POST http://localhost:18000/api/v1/mock/seed/scenario \
  -H "Content-Type: application/json" \
  -d "{\"external_id\":\"demo_physics\",\"parent_name\":\"赵女士\",\"student_name\":\"赵一凡\",\"grade\":\"高一\",\"school\":\"市一中\",\"stage\":\"senior\",\"append_messages\":false,\"messages\":[{\"direction\":\"in\",\"content\":\"高一物理差，想试听一对一\"}]}"

# 3) 换票拿 token（advisor）
curl -X POST http://localhost:18000/api/v1/auth/wecom/exchange \
  -H "Content-Type: application/json" \
  -d "{\"code\":\"mock_code\",\"external_userid\":\"demo_physics\"}"

# 4) 生成画像（替换 CUSTOMER_ID / TOKEN）
curl -X POST http://localhost:18000/api/v1/sidebar/profile/generate \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"customer_id\":CUSTOMER_ID,\"force\":true}"
```

也可用 `Authorization: Bearer mock-<advisor_id>`。

---

## 7. 部署注意

- 宿主机 API 端口为 **18000**（映射容器内 8000）。Windows 上 8000 常落在 Hyper-V 保留段（如 7904–8003）导致 `bind: forbidden`。
- 仅改 API 时：重建 / 重启 `api` 容器即可  
- 侧边栏静态资源由 nginx 挂载 `apps/sidebar/dist`：需在本机执行 sidebar 构建后再刷新页面  
- 经 Nginx 访问仍用 `http://localhost:8080/`（`/api` 反代到容器内 api:8000，不受宿主机映射影响） 

```bash
cd apps/sidebar && npm run build
# 然后按需重启 nginx 或直接刷新（若已挂载 dist）
```

---

## 8. 验收标准

- [ ] `GET /mock/customers` 能看到 demo 与新建客户  
- [ ] `POST /mock/seed/scenario` 可重复调用（同 `external_id` 更新）  
- [ ] 写入不同学科回复后，`force` 生成画像，草稿内容可区分  
- [ ] 侧边栏可切换客户并完成生成 / 确认闭环  
- [ ] 原 `demo_wang` 演示路径仍可用  

---

## 9. 风险与后续

| 项 | 说明 |
|----|------|
| Mock 接口无鉴权 | 仅本地 / 演示环境使用，生产应关闭或加保护 |
| FakeLLM 规则有限 | 只覆盖常见学科关键词；真实差异依赖 DeepSeek |
| 无 Admin 创建客户 | 演示走 `/mock/*`；后台正式创建客户可二期补齐 |
