import argparse
import json
import traceback

class ErrorPlainChineseTranslator:
    """
    后台堆栈报错自动翻译为大白话原因说明与一键自愈建议卡片生成器
    (Error to Plain Chinese Translator and Self-Healing Suggestion Card Generator)
    """

    def __init__(self, mode="json"):
        # default to json if mode is unsupported
        self.mode = mode if mode in ["json", "excel"] else "json"

    def heal_data(self, error_trace: str) -> str:
        """
        Self-heals dirty data (e.g. None or empty string will fallback to a default error).
        """
        if not error_trace or not isinstance(error_trace, str) or not error_trace.strip():
            return "未知异常 (Unknown Error)"
        return error_trace.strip()

    def translate_and_suggest(self, healed_trace: str) -> dict:
        """
        Translates the error trace into plain Chinese and gives self-healing suggestions.
        """
        trace_lower = healed_trace.lower()

        if "syntaxerror" in trace_lower:
            summary = "代码语法错误"
            explanation = "代码中存在拼写或符号错误，导致程序无法理解。"
            suggestion = "请仔细检查标点符号（如漏掉冒号、括号不匹配等）或拼写。"
        elif "filenotfounderror" in trace_lower:
            summary = "找不到文件"
            explanation = "程序试图读取或写入的文件在指定路径下不存在。"
            suggestion = "请检查文件路径是否正确，或者文件是否已经被移动/删除。"
        elif "typeerror" in trace_lower:
            summary = "数据类型不匹配"
            explanation = "程序尝试对错误类型的数据执行操作（如将文字与数字相加）。"
            suggestion = "请检查变量类型，确保使用了正确格式的数据。"
        elif "indexerror" in trace_lower:
            summary = "索引越界"
            explanation = "试图访问列表中不存在的位置的数据。"
            suggestion = "请确认列表长度，确保访问的位置在有效范围内。"
        elif "keyerror" in trace_lower:
            summary = "字典键不存在"
            explanation = "尝试在字典中查找一个不存在的键。"
            suggestion = "请检查字典中是否确实包含您要查找的键。"
        elif "nomodule" in trace_lower or "importerror" in trace_lower:
            summary = "缺少依赖模块"
            explanation = "程序需要用到某个外部工具包，但没有找到。"
            suggestion = "请尝试运行 pip install 安装缺失的模块。"
        else:
            summary = "未知运行时异常"
            explanation = "发生了一些未预料到的错误。"
            suggestion = "请将完整报错信息提供给开发人员，或检查日志以获取更多线索。"

        return {
            "summary": summary,
            "explanation": explanation,
            "suggestion": suggestion,
            "original_trace": healed_trace
        }

    def build_lark_card(self, translation: dict) -> dict:
        """
        Builds a Lark (Feishu) card format.
        Core principles:
        1. Limit core summaries to a maximum of 3 lines.
        2. Place detailed data inside single-click collapsible panels.
        """
        card = {
            "config": {
                "wide_screen_mode": True
            },
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🚨 异常诊断与自愈建议"
                },
                "template": "red"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**问题概览：** {translation['summary']}\n**原因说明：** {translation['explanation']}\n**自愈建议：** {translation['suggestion']}"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "column_set",
                    "flex_mode": "none",
                    "background_style": "default",
                    "columns": [
                        {
                            "tag": "column",
                            "width": "weighted",
                            "weight": 1,
                            "vertical_align": "top",
                            "elements": [
                                {
                                    "tag": "markdown",
                                    "content": "<details><summary>👉 点击展开查看详细堆栈数据</summary>\n\n```\n" + translation['original_trace'] + "\n```\n</details>"
                                }
                            ]
                        }
                    ]
                }
            ]
        }
        return card

    def process_and_output(self, error_trace: str) -> str:
        healed_trace = self.heal_data(error_trace)
        translation = self.translate_and_suggest(healed_trace)
        card = self.build_lark_card(translation)

        if self.mode == "excel":
            # For simplicity, returning a simulated CSV/Excel format as string
            # Columns: 摘要, 原因说明, 自愈建议, 原始堆栈 (Base64 or escaped to avoid CSV breakage, but here we just escape newlines)
            escaped_trace = translation['original_trace'].replace("\n", "\\n").replace(",", "，")
            return f"摘要,原因说明,自愈建议,原始堆栈\n{translation['summary']},{translation['explanation']},{translation['suggestion']},{escaped_trace}"
        else:
            return json.dumps(card, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Error Plain Chinese Translator CLI")
    # Zero parameter one-click execution: we provide default fallback error and mode
    default_error = "Traceback (most recent call last):\n  File \"<stdin>\", line 1, in <module>\nFileNotFoundError: [Errno 2] No such file or directory: 'config.json'"
    parser.add_argument("--error", type=str, default=default_error, help="Error stack trace to translate (optional)")
    parser.add_argument("--mode", type=str, choices=["json", "excel"], default="json", help="Output mode (optional)")

    args = parser.parse_args()

    translator = ErrorPlainChineseTranslator(mode=args.mode)
    output = translator.process_and_output(args.error)
    print(output)

if __name__ == "__main__":
    main()
