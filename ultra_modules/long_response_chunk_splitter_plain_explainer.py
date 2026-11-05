import re
import json

class LongResponseChunkSplitterPlainExplainer:
    """
    超长分析报告语义切分与大白话结论提取器
    后台功能实现严密复杂，支持脏数据自愈、缺参自动设合理默认值。
    前端调用极简。
    """
    def __init__(self, max_chunk_size=1000, default_title="分析报告"):
        # Zero-configuration fault tolerance: Sensible default values
        self.max_chunk_size = max_chunk_size if isinstance(max_chunk_size, int) and max_chunk_size > 0 else 1000
        self.default_title = str(default_title) if default_title else "分析报告"

    def _clean_text(self, text):
        # Silently clean dirty data (None, int, etc.)
        if not isinstance(text, str):
            if text is None:
                return ""
            text = str(text)
        # Remove unprintable characters or weird spaces if necessary, but strip is a good start
        return text.strip()

    def _extract_plain_summary(self, text):
        """
        Extract a 1-second plain summary from the text.
        Finds the first paragraph or conclusion section.
        """
        if not text:
            return "无有效结论。"

        # Look for explicit conclusion indicators
        conclusion_keywords = ["结论：", "总结：", "总之，", "结论:", "总结:"]
        for keyword in conclusion_keywords:
            if keyword in text:
                start_idx = text.find(keyword) + len(keyword)
                # Find end of sentence or paragraph
                end_idx = text.find('\n', start_idx)
                if end_idx == -1:
                    end_idx = len(text)
                snippet = text[start_idx:end_idx].strip()
                if snippet:
                    return f"【核心结论】{snippet}"

        # Fallback: take the first non-empty paragraph
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if line and not re.match(r'^#+', line):
                # Return up to 100 chars
                if len(line) > 100:
                    return f"【极简摘要】{line[:100]}..."
                return f"【极简摘要】{line}"

        return "【极简摘要】详见报告正文。"

    def split_into_chunks(self, report_text, chunk_size=None):
        text = self._clean_text(report_text)
        if not text:
            return [{"title": "摘要", "content": "无内容"}]

        actual_chunk_size = chunk_size if isinstance(chunk_size, int) and chunk_size > 0 else self.max_chunk_size

        # Try to split by markdown headers if they exist, otherwise split by size
        chunks = []
        lines = text.split('\n')
        current_chunk_title = "引言"
        current_chunk_content = []
        current_length = 0

        for line in lines:
            # If a single line is too long, we need to split it so we don't exceed actual_chunk_size by too much
            # But let's first handle the header check
            header_match = re.match(r'^(#{1,3})\s+(.*)', line)

            if header_match:
                if current_chunk_content:
                    content_str = '\n'.join(current_chunk_content).strip()
                    if content_str:
                        chunks.append({
                            "title": current_chunk_title,
                            "content": content_str
                        })
                current_chunk_title = header_match.group(2).strip()
                current_chunk_content = []
                current_length = 0
                continue

            # For normal lines, append and check size
            # If line itself is huge, we split the line into chunks
            if len(line) > actual_chunk_size:
                # First flush current
                if current_chunk_content:
                    content_str = '\n'.join(current_chunk_content).strip()
                    if content_str:
                        chunks.append({
                            "title": current_chunk_title,
                            "content": content_str
                        })
                    current_chunk_title = f"{current_chunk_title} (续)"
                    current_chunk_content = []
                    current_length = 0

                # Then chunk the long line
                start = 0
                while start < len(line):
                    part = line[start:start + actual_chunk_size]
                    chunks.append({
                        "title": current_chunk_title,
                        "content": part
                    })
                    current_chunk_title = f"{current_chunk_title} (续)"
                    start += actual_chunk_size
                continue

            # Normal length line
            if current_length + len(line) > actual_chunk_size and current_chunk_content:
                content_str = '\n'.join(current_chunk_content).strip()
                if content_str:
                    chunks.append({
                        "title": current_chunk_title,
                        "content": content_str
                    })
                current_chunk_title = f"{current_chunk_title} (续)"
                current_chunk_content = []
                current_length = 0

            current_chunk_content.append(line)
            current_length += len(line) + 1

        # Flush last chunk
        if current_chunk_content:
            content_str = '\n'.join(current_chunk_content).strip()
            if content_str:
                chunks.append({
                    "title": current_chunk_title,
                    "content": content_str
                })

        if not chunks:
            chunks = [{"title": "摘要", "content": text}]

        return chunks

    def process(self, report_text, chunk_size=None, format="json"):
        """
        One-click entrypoint: process(text)
        Tolerates missing params, invalid types, etc.
        """
        # Default missing params
        if not isinstance(format, str) or format.lower() not in ["json", "html", "markdown"]:
            format = "json"
        format = format.lower()

        text = self._clean_text(report_text)
        chunks = self.split_into_chunks(text, chunk_size)
        summary = self._extract_plain_summary(text)

        if format == "json":
            cards = []
            # Summary card
            cards.append({
                "header": {"title": {"content": f"{self.default_title} - 1秒速读结论", "tag": "plain_text"}},
                "elements": [{"tag": "markdown", "content": summary}]
            })
            # Detail cards
            for i, chunk in enumerate(chunks):
                cards.append({
                    "header": {"title": {"content": f"{self.default_title} - {chunk['title']}", "tag": "plain_text"}},
                    "elements": [{"tag": "markdown", "content": chunk['content']}]
                })
            return json.dumps(cards, ensure_ascii=False)

        elif format == "markdown":
            cards = [f"# {self.default_title} - 1秒速读结论\n\n{summary}"]
            for i, chunk in enumerate(chunks):
                cards.append(f"## {self.default_title} - {chunk['title']}\n\n{chunk['content']}")
            return "\n\n---\n\n".join(cards)

        elif format == "html":
            html_parts = [f"<div class='feishu-card'><h2>{self.default_title} - 1秒速读结论</h2><p>{summary.replace(chr(10), '<br>')}</p></div>"]
            for i, chunk in enumerate(chunks):
                content_html = chunk['content'].replace(chr(10), '<br>')
                html_parts.append(f"<div class='feishu-card'><h3>{self.default_title} - {chunk['title']}</h3><p>{content_html}</p></div>")
            return "\n".join(html_parts)
