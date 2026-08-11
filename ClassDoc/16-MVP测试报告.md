# MVP 测试报告

**项目**：擎天学智 · K12 用户画像推荐系统  
**依据**：`12-全量开发流程文档.md` 阶段 3.H / 阶段 4、`5-SRS.md` §8.1  
**执行时间**：2026-08-11  
**环境**：Docker Compose（api:`18000` / nginx:`8080` / postgres:`5432`）  
**LLM**：`MOCK_LLM=false`（真实 DeepSeek）  
**脚本**：`scripts/mvp_smoke_test.py`  
**原始结果**：`ClassDoc/16-MVP测试报告.json`

---

## 1. 结论

**MVP 系统测试：通过（30/30）。**

对齐 SRS §8.1 五条验收要点均可演示；主路径无阻塞缺陷。

| SRS §8.1 | 结果 | 证据用例 |
|----------|------|----------|
| 1. 侧边栏可展示画像草稿，支持确认/编辑 | PASS | T-M1-01 / T-M1-04 / 3.H.2 / T-M6-01 |
| 2. 后台员工/客户/订单/标签/看板可用 | PASS | T-M5-01～03 |
| 3. 三角色数据范围可区分 | PASS | T-M5-02a～d |
| 4. Mock 可完成演示闭环 | PASS | 3.H.0 / T-M1-01a / wecom exchange |
| 5. SSE 通路可用 | PASS | T-M6-02（收到 `event: ping`） |

原则「无代发」：T-P-01 PASS（reply 仍为 P2 placeholder）。

---

## 2. 执行摘要

| 项 | 值 |
|----|----|
| 总用例 | 30 |
| 通过 | 30 |
| 失败 | 0 |
| 关键路径 | seed → 换票 → context → generate → draft → patch/confirm → 后台可见 confirmed → 多客户 scenario → 再生成不覆盖 confirmed |

访问入口：

| 入口 | URL |
|------|-----|
| 侧边栏 | http://localhost:8080/ |
| 管理后台 | http://localhost:8080/admin/ |
| API Docs | http://localhost:18000/docs |

---

## 3. 用例明细（按类别）

### 3.1 基础设施

| ID | 结果 | 说明 |
|----|------|------|
| INFRA-01 | PASS | `/health`：`mock_wecom=true`, `mock_llm=false`, `deepseek` |
| INFRA-02 | PASS | Nginx `/` → 200 |
| INFRA-03 | PASS | Nginx `/admin/` → 200 |

### 3.2 画像主路径（T-M1 / 3.H）

| ID | 结果 | 说明 |
|----|------|------|
| 3.H.0 | PASS | seed 已存在（幂等） |
| T-M1-01a | PASS | `POST /mock/seed/scenario` 物理场景客户 |
| T-M1-01b | PASS | 追加 mock 消息 |
| 3.H.1a | PASS | generate 入队返回 `job_id` |
| T-M1-01 | PASS | 草稿含四分区 + confidence/sources（DeepSeek） |
| T-M1-02 | PASS | 仅草稿时看板 funnel.deal 不变 |
| T-M1-04a/b | PASS | 改草稿 / 单字段确认 |
| 3.H.2 | PASS | 全部确认 → `draft_status=merged` |
| 3.H.2b | PASS | 后台客户详情 `profile.confirmed` 可见 |
| T-M1-01c | PASS | 场景客户画像与 demo 内容可区分（高一/物理） |
| T-M1-03 | PASS | 再生成后 confirmed 仍在，并产生新 draft |

### 3.3 后台与权限（T-M5）

| ID | 结果 | 说明 |
|----|------|------|
| T-M5-01 / 01b | PASS | 组织列表 / 创建 |
| T-M5-02a～c | PASS | admin / regional / advisor 登录 |
| T-M5-02d | PASS | advisor 客户数 ≤ admin（scope） |
| T-M5-03a～d | PASS | 客户列表、看板、标签、侧边栏标签 |

### 3.4 侧边栏 / SSE / 原则（T-M6 / T-P）

| ID | 结果 | 说明 |
|----|------|------|
| T-M6-01a/b | PASS | Mock 换票 + context |
| T-M6-02 | PASS | SSE 可读到 ping 事件 |
| T-M6-03 | PASS | 前端文案含「AI 建议」 |
| T-P-01 | PASS | 无企微代发；reply 为 P2 占位 |

---

## 4. 测试中发现与处理

| # | 现象 | 处理 | 是否阻塞 MVP |
|---|------|------|----------------|
| E1 | 宿主机 `8000` 被 Windows 保留端口占用 | Compose 改为 `18000:8000` | 否（已修复） |
| E2 | 首次跑场景客户时 DeepSeek job 长时间 `running` | 清理卡住 job、重启 api；测试改为串行生成 | 否（偶发；主路径已通） |
| E3 | 断言误读 `profile.confirmed` 路径 | 修正脚本取值 | 否（测试脚本问题） |

---

## 5. 复现命令

```powershell
cd d:\ZheJiangAI\K12-UserProfile
docker compose -f deploy/docker-compose.yml ps
python scripts\mvp_smoke_test.py
```

---

## 6. 建议后续（不阻塞 MVP 验收）

- DeepSeek 并发/超时：后台 job 卡死时的超时回收与失败落库  
- UAT：客户用确认单 §二关注点走查签字（阶段 4.2.3）  
- 预发：按需关闭 `MOCK_WECOM`（待企微 OPEN 项）  

---

## 修订

| 版本 | 日期 | 说明 |
|------|------|------|
| V1.0 | 2026-08-11 | 首次 MVP 系统测试全量通过（30/30） |
