# Unified Chat 入口设计与路由

## 1. 背景与目标

前端只需一个对话入口，将消息交给后端，由后端**自动选择**治理 Copilot、Support（含 ops 桥）、MDM 或 Ops 深度对话等能力，并返回**统一外壳**的响应（含 `routing` 元数据，便于排障与观测）。

**非目标（当前阶段）**

- 不删除既有 `/mdm-assistant/chat`、`/support-agent/chat`、`/ops-agent/chat`、`/governance-copilot/chat`；统一入口与之**并存**，便于迁移与兼容。
- 不在 **仅运维** 部署（`ops_main`）挂载本路由（该形态不包含治理编排依赖）；统一入口挂在 **`main`（unified）** 与 **`governance_main`**。

---

## 2. API 契约

### 2.1 `POST /chat`

**请求体** `UnifiedChatRequest`（在 `src/models/api.py`）

| 字段 | 类型 | 说明 |
|------|------|------|
| `messages` | 同现有 `ChatRequest` | 多轮消息列表 |
| `chatSessionId` | optional string | 会话 ID |
| `stream` | bool，默认 false | `true` 时返回 SSE（见 `ai-doc/functions/Chat_SSE_Streaming_设计与实现.md`） |
| `context` | optional object | 透传给 Support/Ops（如 `scenarioId`）；服务端会从 JWT 合并 `userId` / `username`（见 §2.2） |
| `surface` | enum，默认 `auto` | 见下表 |

### 2.2 可选 JWT 用户绑定（Note 37）

Admin 前端在 `Authorization: Bearer <token>` 下调用 `/chat` 时，路由层通过 `get_optional_user()` 解析 JWT，并向下游 `context` 写入：

| 字段 | 来源 |
|------|------|
| `userId` | JWT `sub`（请求体未显式传时） |
| `username` | JWT `username` |

用途：

- 可选 MySQL 持久化（`CHAT_MYSQL_ENABLED=true`）时，`chat_message.user_id` 与 `chat_conversation.user_id` 绑定
- `GET /admin/chat/conversations` 按当前登录用户列出历史会话

**未带 Bearer** 时行为与改造前一致（匿名会话，仅 Redis）。

### 2.3 `surface` 取值

| 值 | 行为 |
|----|------|
| `auto` | 服务端按 §3 规则自动路由 |
| `governance_copilot` | 固定走 `chat_with_governance_copilot` |
| `support_agent` | 固定走 `chat_with_support_agent` |
| `mdm_assistant` | 固定走 `chat_with_mdm_assistant` |
| `ops_agent` | 固定走 `chat_with_ops_agent`（仅 **unified** 模式；**governance** 模式下返回 501） |

**响应体** `UnifiedChatResponse`

| 字段 | 说明 |
|------|------|
| `content` | 主文本回复 |
| `routing` | `UnifiedRoutingInfo`：`target`、`reason`、`surfaceRequested`、可选 `governanceCapability`、`supportTriageRoute` |
| `metadata` | 下游返回的 metadata 合并（含 `chatSessionId`、工具、triage 等） |
| `capability` / `experience` / `legacyRoute` / `tableContract` / … | 当 `target=governance_copilot` 时与现有 Copilot 响应一致的可选字段 |
| `uiCard` / `responseId` | 当 `target=ops_agent` 时透传 |

---

## 3. `surface=auto` 路由策略（确定性、可测）

优先级自上而下，**先排运维症状，再排治理结构化任务，最后默认 Support**：

1. **Support triage（`persona=support`）**  
   - 若 `route == support_with_ops_diagnosis` → **`support_agent`**（调用现有 `chat_with_support_agent`，含 ops 只读诊断桥）。

2. **Governance capability（`analyze_governance_capability`）**  
   - 若 `capability != "knowledge"`（表契约、Kafka 合同、SQL lineage、mapping review 等）→ **`governance_copilot`**。

3. **默认**  
   - → **`support_agent`**（一般治理知识 + 客户可读口径，与 triage `support_direct` 路径一致）。

**说明**

- 不在 auto 链中默认进入 **`ops_agent`**，避免与 Support 运维桥重复；需要深度 Ops 卡片时客户端设 `surface=ops_agent`（unified）或使用 `/ops-agent/chat`。
- **`mdm_assistant`** 仅通过显式 `surface` 使用（内部/兼容场景）。

---

## 4. 运行形态与挂载

| App | `app.state.service_mode` | 是否挂载 `/chat` |
|-----|--------------------------|------------------|
| `create_unified_app` | `unified` | 是；`ops_agent` 可用 |
| `create_governance_app` | `governance` | 是；`ops_agent` 返回 501 |
| `create_ops_app` | `ops` | 否 |

---

## 5. 观测与后续

- 每次路由打结构化日志：`service_mode`、`target`、`reason`、`surface`。
- 后续可加：金标集离线评测、`routing` 指标看板、与意图 LLM 仲裁衔接（见前文「路由一等公民」讨论）。

---

## 6. 与既有接口关系

```text
POST /chat  (新)
  -> unified_chat_router_service.dispatch_unified_chat | dispatch_unified_chat_stream
       -> chat_with_* | stream_* (support / mdm / ops)

POST /support-agent/chat  (保留)
POST /governance-copilot/chat  (保留)
...
```

---

**最后更新**：2026-06-23
