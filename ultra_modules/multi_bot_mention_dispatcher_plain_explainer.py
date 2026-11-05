import json

def to_int_safe(val, default=0):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default

def explain_multi_bot_results(results_data):
    """
    Translates complex backend results from multiple bots into a simple plain-text/Markdown explainer card.
    Expected bots: da_fei_yu, zhao_pin, shu_ju, liang_hua
    """
    if not isinstance(results_data, dict):
        results_data = {}

    # Extract bot specific results with empty dict fallback
    da_fei_yu = results_data.get("da_fei_yu") or {}
    zhao_pin = results_data.get("zhao_pin") or {}
    shu_ju = results_data.get("shu_ju") or {}
    liang_hua = results_data.get("liang_hua") or {}

    if not isinstance(da_fei_yu, dict): da_fei_yu = {}
    if not isinstance(zhao_pin, dict): zhao_pin = {}
    if not isinstance(shu_ju, dict): shu_ju = {}
    if not isinstance(liang_hua, dict): liang_hua = {}

    # Clean and process data for DaFeiYu (Big Fat Fish)
    # Assume it returns 'fish_caught' and 'weight'
    fish_caught = to_int_safe(da_fei_yu.get("fish_caught"), 0)
    weight = to_int_safe(da_fei_yu.get("weight"), 0)
    dafeiyu_text = f"🐟 大肥鱼: 抓到了 {fish_caught} 条鱼，总重 {weight} 斤。"

    # Clean and process data for ZhaoPin (Recruitment)
    # Assume it returns 'candidates' and 'interviews'
    candidates = to_int_safe(zhao_pin.get("candidates"), 0)
    interviews = to_int_safe(zhao_pin.get("interviews"), 0)
    zhaopin_text = f"👔 招聘: 收到 {candidates} 份简历，安排了 {interviews} 场面试。"

    # Clean and process data for ShuJu (Data)
    # Assume it returns 'active_users' and 'revenue'
    active_users = to_int_safe(shu_ju.get("active_users"), 0)
    revenue = to_int_safe(shu_ju.get("revenue"), 0)
    shuju_text = f"📊 数据: 活跃用户 {active_users} 人，营收 {revenue} 元。"

    # Clean and process data for LiangHua (Quantization)
    # Assume it returns 'trades' and 'profit'
    trades = to_int_safe(liang_hua.get("trades"), 0)
    profit = to_int_safe(liang_hua.get("profit"), 0)
    lianghua_text = f"📈 量化: 执行了 {trades} 笔交易，总利润 {profit} 元。"

    # Generate title
    total_metrics = fish_caught + candidates + active_users + trades
    if total_metrics == 0:
        summary_title = "📉 综合汇报: 暂无明显进展。"
    elif total_metrics < 100:
        summary_title = "📊 综合汇报: 业务平稳推进中。"
    else:
        summary_title = "🚀 综合汇报: 业务高速增长中！"

    # Assemble markdown
    markdown_card = f"""# {summary_title}

**各部门详细数据:**
- {dafeiyu_text}
- {zhaopin_text}
- {shuju_text}
- {lianghua_text}

*一键生成的简易白话报告，无门槛阅读体验！*"""

    return {
        "title": summary_title,
        "markdown": markdown_card,
        "raw_clean": {
            "da_fei_yu": {"fish_caught": fish_caught, "weight": weight},
            "zhao_pin": {"candidates": candidates, "interviews": interviews},
            "shu_ju": {"active_users": active_users, "revenue": revenue},
            "liang_hua": {"trades": trades, "profit": profit}
        }
    }
