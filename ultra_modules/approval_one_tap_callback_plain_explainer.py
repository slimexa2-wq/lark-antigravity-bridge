import json
from typing import Any, Dict, Optional


class ApprovalOneTapCallbackPlainExplainer:
    """
    高危外发动作飞书卡片‘一键批准/一键驳回’免跳转回调状态同步器。
    将复杂后台计算结果转化为普通业务人员1秒看懂的大白话结论卡，
    同时提供免跳转回调同步处理。
    """

    @staticmethod
    def generate_card(
        action_name: Any = None,
        risk_level: Any = None,
        backend_result: Any = None,
        operator: Any = None,
    ) -> Dict[str, Any]:
        """
        生成大白话结论卡。
        支持缺参默认兜底、脏数据自愈、复杂数据格式化。
        """
        # 脏数据自愈与缺参默认兜底
        action = (
            str(action_name).strip()
            if action_name is not None and str(action_name).strip()
            else "未知高危操作"
        )

        risk_str = str(risk_level).strip().upper() if risk_level is not None else "CRITICAL"
        if risk_str not in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            risk_str = "CRITICAL"  # 默认未知一律视作最高级

        operator_name = (
            str(operator).strip()
            if operator is not None and str(operator).strip()
            else "未知系统/人员"
        )

        # 处理后台结果
        details = {}
        try:
            if isinstance(backend_result, str):
                parsed = json.loads(backend_result)
                if isinstance(parsed, dict):
                    details = parsed
                else:
                    details = {"raw_parsed": str(parsed)}
            elif isinstance(backend_result, dict):
                details = backend_result
            else:
                details = {"raw": str(backend_result)}
        except Exception:
            details = {"raw_error": str(backend_result)}

        # 极简大白话摘要
        summary_lines = [
            f"⚠️ 警告：检测到【{risk_str}】级别的高危外发动作！",
            f"👉 操作内容：{action}",
            f"👤 操作发起者：{operator_name}",
            "---",
            "后台计算详情摘要：",
        ]

        if not details:
            summary_lines.append("（无附加信息）")
        else:
            for k, v in details.items():
                if k == "raw" and v == "None":
                    summary_lines.append("（无附加信息）")
                    continue
                safe_k = str(k).strip()[:50]
                safe_v = str(v).strip()[:200]
                summary_lines.append(f"- {safe_k}: {safe_v}")

        summary_lines.append("---")
        summary_lines.append("请确认是否允许此操作。一键批准或驳回。")

        markdown_text = "\n".join(summary_lines)

        html_text = markdown_text.replace("\n", "<br>").replace("⚠️", "<b>⚠️</b>").replace("👉", "<b>👉</b>")

        # 飞书卡片格式 (简化版 JSON)
        lark_card_json = {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": f"高危操作审批：{action}"},
                "template": "red" if risk_str in ("HIGH", "CRITICAL") else "orange",
            },
            "elements": [
                {"tag": "markdown", "content": markdown_text},
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "一键批准"},
                            "type": "primary",
                            "value": {"action": "approve", "target": action},
                        },
                        {
                            "tag": "button",
                            "text": {"tag": "plain_text", "content": "一键驳回"},
                            "type": "danger",
                            "value": {"action": "reject", "target": action},
                        },
                    ],
                },
            ],
        }

        return {
            "markdown": markdown_text,
            "html": html_text,
            "lark_card_json": lark_card_json,
        }

    @staticmethod
    def sync_callback_status(callback_payload: Any = None) -> Dict[str, Any]:
        """
        同步免跳转回调状态。
        自动处理脏数据、解析错误，统一返回标准化结果。
        """
        if not callback_payload:
            return {"status": "error", "message": "回调负载为空", "action": "unknown"}

        payload = {}
        try:
            if isinstance(callback_payload, str):
                payload = json.loads(callback_payload)
            elif isinstance(callback_payload, dict):
                payload = callback_payload
            else:
                return {"status": "error", "message": "无效的回调格式", "action": "unknown"}
        except Exception:
            return {"status": "error", "message": "无法解析的回调数据", "action": "unknown"}

        if not isinstance(payload, dict):
            return {"status": "error", "message": "回调数据不是字典格式", "action": "unknown"}

        # 提取操作和目标
        action_value = payload.get("action", "")
        if not action_value and isinstance(payload.get("value"), dict):
            action_value = payload.get("value", {}).get("action", "")

        if not action_value:
            action_value = "unknown"

        safe_action = str(action_value).strip().lower()

        if safe_action in ("approve", "approved", "yes", "true", "1"):
            return {"status": "success", "message": "操作已批准", "action": "approve"}
        elif safe_action in ("reject", "rejected", "no", "false", "0"):
            return {"status": "success", "message": "操作已驳回", "action": "reject"}
        else:
            return {
                "status": "error",
                "message": f"未知的操作指令: {safe_action[:20]}",
                "action": safe_action[:20],
            }
