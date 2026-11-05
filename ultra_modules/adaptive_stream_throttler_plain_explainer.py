import json
import logging
from typing import Dict, Any, Optional, Union

# Optional try-except block just to suppress basic unhandled logger configs
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdaptiveStreamThrottlerPlainExplainer:
    """
    Translates complex stream throttling and sequence lock metrics into plain, easy-to-read
    business language summary cards.
    """

    def __init__(self) -> None:
        pass

    def _sanitize_data(self, metrics: Any) -> Dict[str, Any]:
        """
        Silently handle dirty data. Convert input to dict.
        """
        if not isinstance(metrics, dict):
            if hasattr(metrics, '__dict__'):
                metrics = metrics.__dict__
            else:
                try:
                    metrics = dict(metrics)
                except Exception:
                    metrics = {}

        # Copy to avoid mutating original
        clean = dict(metrics)
        return clean

    def explain(self, metrics: Optional[Union[Dict[str, Any], Any]] = None, format_type: str = 'markdown') -> str:
        """
        Zero-configuration default method to generate an explanation card.
        """
        return self.generate_explanation_card(metrics, format_type)

    def generate_explanation_card(self, metrics: Optional[Union[Dict[str, Any], Any]] = None, format_type: str = 'markdown') -> str:
        """
        Generates a summary card explaining the adaptive stream throttler's status.

        Args:
            metrics: The raw metrics from the throttler.
            format_type: The output format: 'html', 'json', or 'markdown'.

        Returns:
            A formatted string containing the plain language explanation.
        """
        # Sensible defaults for missing params
        if metrics is None:
            metrics = {}

        metrics = self._sanitize_data(metrics)

        # 150ms ~ 500ms dynamic window boundary clamping
        raw_window = metrics.get('current_window_ms')

        try:
            window_ms = float(raw_window) if raw_window is not None else 300.0
            if window_ms < 150.0:
                window_ms = 150.0
            elif window_ms > 500.0:
                window_ms = 500.0
        except (ValueError, TypeError):
            window_ms = 300.0 # sensible default

        # Sequence lock info
        seq_num = metrics.get('sequence_number')
        try:
            seq_num = int(seq_num) if seq_num is not None else 0
        except (ValueError, TypeError):
            seq_num = 0

        # Traffic status interpretation
        dropped_msgs = metrics.get('dropped_messages')
        try:
            dropped_msgs = int(dropped_msgs) if dropped_msgs is not None else 0
            if dropped_msgs < 0:
                dropped_msgs = 0
        except (ValueError, TypeError):
            dropped_msgs = 0

        status = "正常 (Normal)"
        if window_ms >= 450:
            status = "拥堵 (Congested) - 推送降速中"
        elif window_ms <= 200:
            status = "畅通 (Smooth) - 极速推送中"

        # Create plain language dictionary
        data = {
            "title": "飞书流式卡片推送状态摘要",
            "status": status,
            "window_ms": f"{window_ms:.1f}毫秒",
            "sequence": str(seq_num),
            "dropped": str(dropped_msgs),
            "conclusion": f"当前节流窗口为{window_ms:.1f}毫秒。系统拦截了{dropped_msgs}条冗余消息，保证了卡片最新序号为{seq_num}，且平稳送达用户。"
        }

        # Output formatting
        format_type = str(format_type).lower().strip()

        if format_type == 'html':
            return self._format_html(data)
        elif format_type == 'json':
            return self._format_json(data)
        else:
            # Fallback to markdown for everything else
            return self._format_markdown(data)

    def _format_markdown(self, data: Dict[str, str]) -> str:
        return f"""# {data['title']}
- **当前状态:** {data['status']}
- **推送间隔:** {data['window_ms']}
- **最新序号:** {data['sequence']}
- **拦截冗余:** {data['dropped']}条

**大白话总结:**
{data['conclusion']}
"""

    def _format_html(self, data: Dict[str, str]) -> str:
        return f"""<div class="throttler-card">
  <h2>{data['title']}</h2>
  <ul>
    <li><strong>当前状态:</strong> {data['status']}</li>
    <li><strong>推送间隔:</strong> {data['window_ms']}</li>
    <li><strong>最新序号:</strong> {data['sequence']}</li>
    <li><strong>拦截冗余:</strong> {data['dropped']}条</li>
  </ul>
  <p><strong>大白话总结:</strong><br/>{data['conclusion']}</p>
</div>"""

    def _format_json(self, data: Dict[str, str]) -> str:
        return json.dumps(data, ensure_ascii=False, indent=2)
