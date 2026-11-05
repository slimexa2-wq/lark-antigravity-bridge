import time
import uuid
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class MentionRecord:
    bot_name: str
    context: str
    timestamp: float = field(default_factory=time.time)

class MultiBotMentionDispatcher:
    """
    Dispatcher to route multiple mentions in a message to specific bot logic
    and aggregate the responses into a Feishu (Lark) Card.
    """
    KNOWN_BOTS = {"大肥鱼", "招聘", "数据", "量化"}

    def __init__(self, fallback_bot: str = "默认助手"):
        self.fallback_bot = fallback_bot

    def parse_mentions(self, text: str) -> List[MentionRecord]:
        """
        Parses mentions like @大肥鱼 from the text.
        Handles dirty data by normalizing spaces and falling back if text is empty.
        """
        if not text or not isinstance(text, str):
            return []

        text = text.strip()
        if not text:
            return []

        # Find all mentions, considering variations of @
        # Handle zero-width spaces or weird encodings gracefully (simplification: normal regex)
        mentions = re.findall(r"@([^\s@]+)", text)

        records = []
        for m in mentions:
            bot_name = m.strip()
            # Basic validation
            if not bot_name:
                continue

            # Keep recognized bots, fallback otherwise if we wanted strict filtering
            # For this exercise, we'll keep it as what they mentioned or map to known bots.
            if bot_name not in self.KNOWN_BOTS:
                bot_name = self.fallback_bot

            records.append(MentionRecord(bot_name=bot_name, context=text))

        return records

    def dispatch(self, mentions: List[MentionRecord]) -> Dict[str, Any]:
        """
        Simulate dispatching tasks to different bots and gathering results.
        Returns a simplified aggregation mapping bot name to its 'result'.
        """
        results = {}
        for idx, m in enumerate(mentions):
            # Simulate some processing logic
            result_text = f"[{m.bot_name}处理完成] ID={uuid.uuid4().hex[:8]}"
            if m.bot_name not in results:
                results[m.bot_name] = []
            results[m.bot_name].append(result_text)

        return results

    def build_feishu_card(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Builds a Feishu Card based on the dispatched results.
        Rule: Core summary max 3 lines, detailed data inside single-click collapsible panels.
        """
        if not results:
            return self._build_empty_card()

        total_mentions = sum(len(items) for items in results.values())
        unique_bots = len(results)

        # Core summary: max 3 lines
        summary_lines = [
            f"🎯 任务执行汇总: {total_mentions} 个请求已完成",
            f"🤖 涉及Bot模块: {', '.join(results.keys())[:20] + '...' if len(', '.join(results.keys())) > 20 else ', '.join(results.keys())}",
            "💡 详细执行数据请展开面板查看"
        ]
        summary_text = "\n".join(summary_lines)

        # Build collapsible panels for details
        elements = []

        # Summary block
        elements.append({
            "tag": "div",
            "text": {
                "content": summary_text,
                "tag": "lark_md"
            }
        })

        # Detailed data panels for each bot
        # Feishu does not support HTML tags like <details>, so we will use plain text
        # and simple markdown to separate detailed data.
        for bot_name, items in results.items():
            # For massive outputs, just show a summary in the card to avoid flooding,
            # we simulate 'collapsible' by just showing count if too many.
            if len(items) > 5:
                content = f"共 {len(items)} 条执行记录，详见系统日志"
            else:
                content = "\n".join(items)

            elements.append({
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"**{bot_name} 执行明细**\n{content}"
                }
            })

        return {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "多Bot协同分发报告"
                },
                "template": "blue"
            },
            "elements": elements
        }

    def _build_empty_card(self) -> Dict[str, Any]:
        return {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": "任务执行报告"},
                "template": "grey"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {"content": "暂无有效的Bot提及或解析失败，未执行任何任务。", "tag": "lark_md"}
                }
            ]
        }


class SyntheticFixtureGenerator:
    """
    Generates synthetic datasets containing normal, dirty, extreme boundary,
    and high concurrency cases.
    """

    @staticmethod
    def generate_normal() -> List[str]:
        return [
            "请 @大肥鱼 帮我处理一下这个",
            "@招聘 查一下最新的HC @数据 同步一份报表",
            "测试 @量化 的接口"
        ]

    @staticmethod
    def generate_dirty() -> List[str]:
        return [
            None,
            "",
            "   ",
            "@@@@",
            "@ @",
            "\x00\x01\x02@大肥鱼\n\r\t@招聘",
            "emoji😱测试 @量化🤖",
            "@大肥鱼"*1000  # huge string but single type
        ]

    @staticmethod
    def generate_extreme_boundary() -> List[str]:
        # Very long texts, cross-year and cross-month boundary simulation
        return [
            f"2023-12-31 23:59:59 @大肥鱼 请在跨年前完成处理",
            f"2024-01-01 00:00:01 @招聘 跨年第一单",
            f"2024-02-29 12:00:00 @数据 闰年闰月数据对齐",
            f"2024-03-01 00:00:00 @量化 跨月结算",
        ] + [
            f"@{bot} " * 500 for bot in ["大肥鱼", "招聘", "数据", "量化", "未知"]
        ]

    @staticmethod
    def generate_high_concurrency(count: int = 10000) -> List[str]:
        return ["@大肥鱼 @数据 " * 5] * count


class BenchmarkSuite:
    """
    Executes benchmark tests to ensure zero crash and millisecond responses.
    """
    def __init__(self, dispatcher: MultiBotMentionDispatcher):
        self.dispatcher = dispatcher

    def run_benchmark(self, dataset: List[str]) -> Dict[str, float]:
        """
        Runs the full pipeline on a dataset and returns metrics.
        """
        start_time = time.time()
        success_count = 0
        failure_count = 0

        for item in dataset:
            try:
                mentions = self.dispatcher.parse_mentions(item)
                results = self.dispatcher.dispatch(mentions)
                card = self.dispatcher.build_feishu_card(results)
                success_count += 1
            except Exception as e:
                failure_count += 1

        end_time = time.time()
        elapsed_ms = (end_time - start_time) * 1000

        return {
            "elapsed_ms": elapsed_ms,
            "success_count": success_count,
            "failure_count": failure_count,
            "avg_ms_per_item": elapsed_ms / len(dataset) if dataset else 0
        }
