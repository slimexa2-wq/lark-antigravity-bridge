> 🚨 **最高统帅原则（效率第一 · 后台复杂 · 前端极简 · 严禁过度安全）**：
> 1. **严禁过度安全恶心用户**：砍掉一切冗余的二次确认令牌、繁琐弹窗拦截、机械必填报错与人为卡点；常规操作采用“一键直达 + 后台自动快照备份 + 随时可撤回”。
> 2. **后台复杂、前端极简**：所有格式兼容、脏数据清洗、漏填状态补齐、四方公式核对、跨表勾稽全部封装在后台自动完成；前端交互必须做到傻瓜式直观（1 步输入/拖入 → 1 键出定稿结果），便捷所有使用者！
> 3. **Top 50 开源标杆融合**：详见同目录 `docs/TOP50_OPEN_SOURCE_FUSION.md`。

# 飞书 × Antigravity 多 Agent 实时流式桥接器深度调研与演进蓝图（四源对标版）

> **调研基线**：本蓝图综合 **① 本公司飞书移动办公与多 Agent 远程操控场景**、**② 标杆产品（飞书智能伙伴 CardKit v2 / Vercel Chat SDK / Linear Slack Agent）**、**③ 优秀开源项目（`larksuite/lark-openapi-mcp` / `agent-to-feishu` / LangGraph HITL）** 与 **④ 人机协同有界自治论文（Bounded Autonomy & Human-in-the-Loop Agentic Systems）**，指导 `lark-antigravity-bridge` 的核心功能完善。

---

## 一、四源深度调研矩阵

### 1. 本公司真实业务场景与核心痛点
- **核心场景**：通过飞书（Feishu/Lark）随时随地向本机 Antigravity / Codex / Spider 舰队下达指令（如触发周期报表核算、查询供应商提成审核进度、查看 BidOS 标书解析结果、审批高风险操作）。
- **真实技术痛点**：
  1. **流式打字机限流与乱序**：飞书卡片更新接口有严格的频率限制（Rate Limit），高频 Token 流直接触发卡片 PATCH 会导致 HTTP 429 限流或旧序号覆盖新内容。
  2. **长文本与截断 JSON 容错**：Agent 流式输出未闭合的 Markdown 代码块、表格或半截 JSON 时，卡片渲染易报错或闪烁。
  3. **三档权限人机协同审批（HITL）**：按照全局准则第 4 条（直接做 / 先备份再做 / 必须经我批准），当 Agent 触及“删除数据、产生费用、对外发送、不可逆操作”时，必须在飞书端弹出可交互的 **【批准执行 / 驳回修改】审批卡片**，点击后精准唤醒挂起的会话继续执行。

### 2. 同类标杆商业产品对标
- **飞书智能伙伴 (Feishu AI Agent & CardKit Streaming)**：借鉴其“思考过程可折叠面板（Collapsible Reasoning/Tool Panel）+ 正文流式输出 + 底部快捷追问按钮”三段式卡片布局。
- **Vercel Chat SDK & Linear Agent**：借鉴其多轮线程状态绑定（`chat_id + message_id ↔ session_id`）与任务进度条实时刷新体验。

### 3. 优秀开源项目借鉴
- **`larksuite/lark-openapi-mcp` & `WSClient`**：基于飞书长连接（WebSocket）实现零公网 IP 暴露的事件订阅与卡片回调接收，内置指数退避重连与事件 `event_id` 幂等去重（防止飞书超时重推导致任务重复执行）。
- **LangGraph `interrupt()` / `resume` 模式**：将高风险操作封装为带状态检查点（Checkpoint）的挂起态，通过飞书卡片 `card.action.trigger` 回调恢复执行。

### 4. 学术论文与工程方法支撑
- **Adaptive Token Throttling & Incremental Markdown Repair for Streaming UIs**：采用自适应窗口节流（Adaptive Coalescing Buffer：首包 `<100ms` 立即响应，后续按 `250ms~400ms` 或语义换行合批发送，遇 429 自动退避）+ 未闭合代码块/表格自动补全闭合标签（Incremental Markdown Sanitizer），确保流式渲染 0 报错、0 乱序。

---

## 二、分阶段功能完善与工程演进路线图

### Phase 1：自适应流式卡片节流器、单调序号锁与半截 Markdown/JSON 自愈引擎（`src/`）
1. 实现 **AdaptiveStreamThrottler**：支持首包极速上屏、后续 Token 合批防抖、严格单调递增 `sequence` 序号锁（丢弃乱序过期帧）与 HTTP 429 指数退避重试，确保终态 100% 送达。
2. 实现 **IncrementalMarkdownAndJsonRepair**：在流式渲染中间态自动闭合未结束的 ``` 代码块、表格与 JSON 结构，并针对超长输出自动分页或生成本地/云端完整报告链接。

### Phase 2：事件幂等去重、工具调用状态折叠面板与 HITL 交互审批链路（`src/` + `tests/`）
1. 增加飞书 `event_id / message_id` LRU 幂等去重池，彻底杜绝飞书重推事件引发重复执行。
2. 支持将 Agent 工具调用（Tool Call）与子任务进度渲染为卡片可折叠状态栏，并提供高风险操作 HITL 审批状态机与完整 Vitest 单元测试套件。
