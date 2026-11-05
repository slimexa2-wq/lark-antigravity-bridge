import json

class MobileTableDigestFormatter:
    """
    飞书手机端宽表自动转为3行核心摘要+高亮异常项+完整附件下载卡片器。
    提供极简前端调用，零配置容错，脏数据自愈，缺参自动设合理默认值。
    """

    def __init__(self):
        pass

    def format(self, data=None, format_type="markdown", title="数据摘要分析", anomaly_keys=None):
        """
        核心方法：将宽表数据转换为精简的摘要卡片。

        参数:
        - data: 原始宽表数据 (期望 list of dicts，但具有自愈能力)
        - format_type: 输出格式 ("markdown", "html", "json")，默认 "markdown"
        - title: 摘要标题，缺省自动使用默认值
        - anomaly_keys: 需要特别检查异常的键名列表，缺省为None
        """
        # 1. 缺参默认兜底与脏数据自愈
        if data is None:
            data = []

        format_type = str(format_type).lower().strip() if format_type else "markdown"
        if format_type not in ["markdown", "html", "json"]:
            format_type = "markdown"

        if not title or not isinstance(title, str):
            title = "数据摘要分析"

        if anomaly_keys is None or not isinstance(anomaly_keys, list):
            anomaly_keys = []

        valid_data = self._heal_and_sanitize_data(data)

        # 2. 提取3行核心摘要
        digest_lines = self._generate_3_line_digest(valid_data)

        # 3. 高亮异常项
        anomalies = self._detect_anomalies(valid_data, anomaly_keys)

        # 4. 生成完整附件下载卡片器数据
        attachment_card = self._generate_attachment_card(valid_data)

        # 5. 渲染输出
        return self._render(format_type, title, digest_lines, anomalies, attachment_card)

    def _heal_and_sanitize_data(self, raw_data):
        """脏数据自愈：确保返回 list of dicts"""
        if isinstance(raw_data, dict):
            return [raw_data]
        if not isinstance(raw_data, list):
            try:
                # 尝试将非结构化数据转化为单个元素的列表
                if raw_data:
                    return [{"raw_value": str(raw_data)}]
                return []
            except Exception:
                return []

        sanitized = []
        for item in raw_data:
            if isinstance(item, dict):
                sanitized.append(item)
            elif item is not None:
                sanitized.append({"_raw": str(item)})
        return sanitized

    def _generate_3_line_digest(self, data):
        """提取大白话结论卡：3行核心摘要"""
        total = len(data)
        if total == 0:
            return [
                "1. 数据总览：当前未接收到有效数据记录。",
                "2. 状态评估：暂无业务数据可供分析。",
                "3. 核心指标：所有数值指标均为空。"
            ]

        # 尝试汇总数值
        numeric_sums = {}
        has_data = False
        for row in data:
            for k, v in row.items():
                # 过滤掉内部自愈用的key
                if k.startswith("_raw"):
                    continue
                has_data = True
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    numeric_sums[k] = numeric_sums.get(k, 0) + v
                elif isinstance(v, str):
                    try:
                        val = float(v.replace(",", ""))
                        numeric_sums[k] = numeric_sums.get(k, 0) + val
                    except ValueError:
                        pass

        line1 = f"1. 数据总览：共处理 {total} 条有效数据记录。"

        if not has_data:
            line2 = "2. 状态评估：数据缺少有效业务字段。"
            line3 = "3. 核心指标：无法计算。"
        elif numeric_sums:
            top_metric = max(numeric_sums.items(), key=lambda x: x[1])
            line2 = "2. 状态评估：业务数据加载与解析正常。"
            line3 = f"3. 核心指标：[{top_metric[0]}] 汇总值为 {top_metric[1]:.2f}。"
        else:
            line2 = "2. 状态评估：以文本数据为主，未见严重缺失。"
            line3 = "3. 核心指标：无明显数值型数据可汇总。"

        return [line1, line2, line3]

    def _detect_anomalies(self, data, anomaly_keys):
        """发现异常：高亮显示"""
        anomalies = []
        default_error_keywords = ['error', 'fail', 'failed', '异常', '失败', '超时', 'timeout']

        for i, row in enumerate(data):
            for k, v in row.items():
                str_v = str(v).lower()
                is_anomaly = False

                if anomaly_keys and k in anomaly_keys:
                    # 如果指定了键，值为空或者负数也被视为异常
                    if v is None or str_v == "" or (isinstance(v, (int, float)) and v < 0):
                        is_anomaly = True

                # 检查默认异常关键字
                if any(kw in str_v for kw in default_error_keywords):
                    is_anomaly = True

                if is_anomaly:
                    anomalies.append(f"第 {i+1} 行发现异常 -> {k}: {v}")

        # 限制异常数量，防止信息爆炸
        if len(anomalies) > 5:
            anomalies = anomalies[:5] + [f"...及其他 {len(anomalies) - 5} 项异常隐藏"]

        return anomalies

    def _generate_attachment_card(self, data):
        """生成完整附件下载卡片数据"""
        total = len(data)
        size_est = total * 128  # 简单预估大小
        size_str = f"{size_est / 1024:.1f} KB" if size_est > 0 else "未知大小"

        return {
            "title": "📊 完整数据底表",
            "file_name": "full_data_export.xlsx",
            "file_size": size_str,
            "url": "https://example.com/api/download/full_data_export.xlsx",
            "action_text": "点击下载完整附件"
        }

    def _render(self, format_type, title, digest_lines, anomalies, card):
        if format_type == "json":
            return json.dumps({
                "title": title,
                "digest": digest_lines,
                "anomalies": anomalies,
                "attachment_card": card
            }, ensure_ascii=False)

        elif format_type == "html":
            html = f'<div class="digest-card" style="font-family: sans-serif;">\n'
            html += f'  <h3 style="margin-bottom: 8px;">{title}</h3>\n'
            html += f'  <div class="core-digest" style="background-color: #f5f6f7; padding: 10px; border-radius: 4px;">\n'
            for line in digest_lines:
                html += f'    <div style="margin-bottom: 4px;">{line}</div>\n'
            html += f'  </div>\n'

            if anomalies:
                html += f'  <div class="anomalies" style="margin-top: 12px; color: #d83931;">\n'
                html += f'    <b>⚠️ 异常高亮：</b>\n    <ul style="margin-top: 4px; padding-left: 20px;">\n'
                for anom in anomalies:
                    html += f'      <li>{anom}</li>\n'
                html += f'    </ul>\n  </div>\n'

            html += f'  <div class="attachment" style="margin-top: 16px; padding: 12px; border: 1px solid #dee0e3; border-radius: 6px; display: flex; justify-content: space-between; align-items: center;">\n'
            html += f'    <div>\n      <b>{card["title"]}</b><br/>\n'
            html += f'      <span style="color: #8f959e; font-size: 12px;">{card["file_name"]} ({card["file_size"]})</span>\n    </div>\n'
            html += f'    <a href="{card["url"]}" style="text-decoration: none; color: #3370ff; font-weight: 500;">{card["action_text"]}</a>\n'
            html += f'  </div>\n</div>'
            return html

        else: # markdown
            md = f"## {title}\n\n"
            md += "**🎯 核心摘要**\n"
            for line in digest_lines:
                md += f"> {line}\n"
            md += "\n"

            if anomalies:
                md += "**⚠️ 异常高亮**\n"
                for anom in anomalies:
                    md += f"- {anom}\n"
                md += "\n"

            md += "---\n"
            md += f"**📎 附件下载卡片**\n"
            md += f"[{card['title']}]({card['url']}) | `{card['file_name']}` ({card['file_size']})\n"
            md += f"*{card['action_text']}*\n"
            return md
