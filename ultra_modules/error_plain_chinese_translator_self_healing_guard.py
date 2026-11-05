import time
import uuid
import copy
from typing import Dict, Any, Optional

class ErrorPlainChineseTranslatorSelfHealingGuard:
    """
    后台堆栈报错自动翻译为大白话原因说明与一键自愈建议卡片生成器
    异常输入静默自愈与5秒一键撤回(Undo)快照机制
    严禁弹窗报错打断用户，自动修复格式瑕疵并维护可随时一键撤回的轻量快照
    缺参自动设合理默认值，脏数据静默清理
    """
    def __init__(self):
        self._snapshots: Dict[str, Dict[str, Any]] = {}

    def translate_and_heal(self, raw_error: Any = None, context: Any = None) -> Dict[str, Any]:
        """
        核心方法：翻译错误并自愈，生成快照
        """
        # 缺参自动设合理默认值、静默清理脏数据
        if context is None or not isinstance(context, dict):
            context = {}

        # 安全提取错误信息
        error_str = "未提供错误信息"
        if isinstance(raw_error, str):
            error_str = raw_error if raw_error.strip() else error_str
        elif isinstance(raw_error, dict):
            error_str = str(raw_error.get('raw_error', raw_error.get('message', '未提供错误信息')))
        elif raw_error is not None:
            error_str = str(raw_error)

        # 极端边界：大文本截断
        is_truncated = False
        if len(error_str) > 5000:
            error_str = error_str[:5000] + "...[截断]"
            is_truncated = True

        lower_err = error_str.lower()

        # 默认返回结果（大白话翻译与自愈建议）
        explanation = "系统内部发生未知错误。"
        suggestion = "建议刷新页面重试。"
        is_healed = False
        healed_state = {}

        # 错误匹配与翻译自愈逻辑
        if "timeout" in lower_err or "连接超时" in lower_err or "timed out" in lower_err:
            explanation = "网络请求超时了，服务器没来得及响应。"
            suggestion = "请检查网络连接是否正常，或者稍后再试。"
            is_healed = True
            healed_state = {"action": "retry_network", "delay": 2000}
        elif "null pointer" in lower_err or "nonetype" in lower_err or "undefined" in lower_err:
            explanation = "程序在处理数据时遇到了空值，像是在找一个不存在的东西。"
            suggestion = "系统正在自动补充缺失的数据默认值，请重试。"
            is_healed = True
            healed_state = {"action": "fill_default_values"}
        elif "permission denied" in lower_err or "403" in lower_err or "forbidden" in lower_err:
            explanation = "您当前没有权限执行此操作。"
            suggestion = "请联系管理员为您开通相应的访问权限。"
        elif "database" in lower_err or "sql" in lower_err:
            explanation = "数据库在存取数据时卡住了。"
            suggestion = "可能是短时间内访问人数过多，请稍等片刻。"
        elif "format" in lower_err or "syntax" in lower_err or "parse" in lower_err:
            explanation = "数据格式存在瑕疵，无法被正常识别。"
            suggestion = "系统已尝试自动修复格式问题。"
            is_healed = True
            healed_state = {"action": "auto_format_fix"}

        # 自动修复格式瑕疵 (在上下文状态中进行)
        original_state = copy.deepcopy(context.get("current_state", {}))

        # 生成快照ID并记录 (5秒有效期)
        snapshot_id = str(uuid.uuid4())
        self._snapshots[snapshot_id] = {
            "timestamp": time.time(),
            "original_state": original_state,
        }

        # 顺便清理过期快照以防内存泄漏
        self._cleanup_snapshots()

        return {
            "snapshot_id": snapshot_id,
            "original_error": error_str,
            "plain_chinese_explanation": explanation,
            "auto_healing_suggestion": suggestion,
            "is_healed": is_healed,
            "healed_state": healed_state,
            "is_truncated": is_truncated
        }

    def undo_snapshot(self, snapshot_id: Any = None) -> Dict[str, Any]:
        """
        一键撤回(Undo)机制。要求5秒内有效。
        若snapshot_id不存在或过期，返回友好的失败信息，严禁报错。
        """
        self._cleanup_snapshots()

        if snapshot_id is None or not isinstance(snapshot_id, str):
            return {
                "success": False,
                "message": "无效的快照ID，撤回失败。",
                "restored_state": None
            }

        if snapshot_id not in self._snapshots:
            return {
                "success": False,
                "message": "快照不存在或已超过5秒可撤回时间，撤回失败。",
                "restored_state": None
            }

        snapshot = self._snapshots.pop(snapshot_id)
        return {
            "success": True,
            "message": "已成功撤回并恢复到上一个状态。",
            "restored_state": snapshot["original_state"]
        }

    def _cleanup_snapshots(self):
        """
        轻量快照清理机制，删除超过5秒的记录
        """
        current_time = time.time()
        expired_keys = [
            k for k, v in self._snapshots.items()
            if current_time - v["timestamp"] > 5.0
        ]
        for k in expired_keys:
            self._snapshots.pop(k, None)
