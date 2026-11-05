import json
import html

def generate_explainer_card(command: str, raw_data: dict) -> dict:
    """
    Generates a simplified explainer card (HTML, JSON, Markdown) from raw backend data.
    Ensures maximum 3 lines of summary and hides complex details in collapsible panels.
    Provides extreme fault tolerance, missing parameter fallback, and dirty data self-healing.

    Commands:
        /周报 (weekly report)
        /提成 (commission)
        /漫剧 (comic)
        /标书 (bidding document)
        /状态 (status)
    """

    # 1. Self-healing / Defaults for missing parameters
    if not isinstance(raw_data, dict):
        raw_data = {}

    command = str(command).strip()

    # Command router
    if command == "/周报":
        return _handle_weekly_report(raw_data)
    elif command == "/提成":
        return _handle_commission(raw_data)
    elif command == "/漫剧":
        return _handle_comic(raw_data)
    elif command == "/标书":
        return _handle_bidding(raw_data)
    elif command == "/状态":
        return _handle_status(raw_data)
    else:
        return _handle_fallback(command, raw_data)

def _generate_output(title: str, summary_lines: list, details: dict) -> dict:
    # Ensure max 3 lines for summary
    summary_lines = [str(line) for line in summary_lines if line][:3]
    summary_text = "<br>".join([html.escape(line) for line in summary_lines])
    summary_md = "\n".join(summary_lines)

    details_json = json.dumps(details, ensure_ascii=False, indent=2)
    safe_title = html.escape(title)

    html_output = f"""
<div class="explainer-card">
    <h3>{safe_title}</h3>
    <p class="summary">{summary_text}</p>
    <details>
        <summary>点击查看详情 (Click for details)</summary>
        <pre>{html.escape(details_json)}</pre>
    </details>
</div>
"""

    markdown = f"""### {title}
{summary_md}
<details>
<summary>点击查看详情 (Click for details)</summary>

```json
{details_json}
```
</details>
"""

    return {
        "format": "card",
        "html": html_output.strip(),
        "markdown": markdown.strip(),
        "json": {
            "title": title,
            "summary": summary_lines,
            "details": details
        }
    }

def _handle_weekly_report(raw_data: dict) -> dict:
    completed = raw_data.get("completed_tasks", [])
    if not isinstance(completed, list): completed = []

    pending = raw_data.get("pending_tasks", [])
    if not isinstance(pending, list): pending = []

    summary = [
        f"✅ 已完成: {len(completed)} 项任务",
        f"⏳ 待办中: {len(pending)} 项任务",
        "💡 总结: 本周工作进度正常" if len(completed) >= len(pending) else "💡 总结: 需加快进度"
    ]

    details = {
        "completed": completed,
        "pending": pending,
        "raw_stats": raw_data.get("stats", {})
    }

    return _generate_output("📅 本周工作摘要", summary, details)

def _handle_commission(raw_data: dict) -> dict:
    try:
        amount = float(raw_data.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0.0

    try:
        rate = float(raw_data.get("rate", 0))
    except (ValueError, TypeError):
        rate = 0.0

    try:
        calc_amount = amount * rate if amount and rate else float(raw_data.get("total", 0))
    except (ValueError, TypeError):
        calc_amount = 0.0

    summary = [
        f"💰 预计提成: ¥{calc_amount:.2f}",
        f"📊 业绩基数: ¥{amount:.2f} (费率 {rate*100:.1f}%)",
        "✨ 数据已更新，请核对"
    ]

    details = {
        "base_amount": amount,
        "rate": rate,
        "calculated_total": calc_amount,
        "history": raw_data.get("history", [])
    }

    return _generate_output("💵 提成收益简报", summary, details)

def _handle_comic(raw_data: dict) -> dict:
    title = raw_data.get("title", "未知漫剧")
    views = raw_data.get("views", 0)
    if not isinstance(views, (int, float)):
        views = 0

    summary = [
        f"🎭 剧名: {title}",
        f"👀 播放量: {views} 次",
        f"📈 状态: {'爆款潜质' if views > 10000 else '平稳播放中'}"
    ]

    details = {
        "title": title,
        "views": views,
        "episodes": raw_data.get("episodes", []),
        "comments_count": raw_data.get("comments", 0)
    }

    return _generate_output("🎬 漫剧数据速览", summary, details)

def _handle_bidding(raw_data: dict) -> dict:
    project = raw_data.get("project_name", "未命名项目")
    status = raw_data.get("status", "未知")
    deadline = raw_data.get("deadline", "未设定")

    summary = [
        f"📁 项目: {project}",
        f"📌 状态: {status}",
        f"⏰ 截标时间: {deadline}"
    ]

    details = {
        "project_name": project,
        "status": status,
        "deadline": deadline,
        "requirements": raw_data.get("requirements", []),
        "competitors": raw_data.get("competitors", [])
    }

    return _generate_output("📑 标书进度追踪", summary, details)

def _handle_status(raw_data: dict) -> dict:
    sys_status = raw_data.get("system", "正常")
    cpu = raw_data.get("cpu", "未知")
    mem = raw_data.get("memory", "未知")

    summary = [
        f"🟢 系统状态: {sys_status}",
        f"⚡ CPU使用率: {cpu}",
        f"🧠 内存使用: {mem}"
    ]

    details = {
        "system": sys_status,
        "cpu": cpu,
        "memory": mem,
        "disk": raw_data.get("disk", {}),
        "network": raw_data.get("network", {})
    }

    return _generate_output("🛠️ 系统运行状态", summary, details)

def _handle_fallback(command: str, raw_data: dict) -> dict:
    summary = [
        f"❓ 未知指令: {command}",
        "支持: /周报, /提成, /漫剧, /标书, /状态",
        "已暂存您的原始数据"
    ]

    details = {
        "unrecognized_command": command,
        "raw_data": raw_data
    }

    return _generate_output("⚠️ 指令解析提示", summary, details)
