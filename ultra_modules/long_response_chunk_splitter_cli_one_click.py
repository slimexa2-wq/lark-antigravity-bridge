import argparse
import json
from typing import Any, List, Dict

class LongResponseChunkSplitter:
    """
    Splits long analytical reports or texts into multiple continuous chunks based on semantic boundaries
    (like paragraphs) to be read comfortably in Lark cards.
    """

    def __init__(self, mode: str = "json", max_length: int = 1000):
        self.mode = mode if mode in ["json", "excel"] else "json"
        self.max_length = max_length if isinstance(max_length, int) and max_length > 0 else 1000

    def heal_data(self, text: Any) -> str:
        """
        Self-heals dirty data (e.g., handling None, integers, non-string inputs).
        """
        if text is None:
            return ""
        if not isinstance(text, str):
            try:
                return str(text)
            except Exception:
                return ""
        return text.strip()

    def split_text(self, text: Any) -> List[str]:
        """
        Splits the text into chunks preserving paragraph boundaries (\n\n or \n).
        If a single paragraph is larger than max_length, it is forced to split.
        """
        healed_text = self.heal_data(text)
        if not healed_text:
            return []

        paragraphs = healed_text.split('\n')
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # If a single paragraph is larger than max_length, split it forcefully
            if len(para) > self.max_length:
                # Flush the current chunk if it has content
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # Force split the large paragraph
                for i in range(0, len(para), self.max_length):
                    chunks.append(para[i:i + self.max_length])
                continue

            # If adding this paragraph exceeds max_length, push current_chunk and start new
            if len(current_chunk) + len(para) + (1 if current_chunk else 0) > self.max_length:
                if current_chunk:  # pragma: no branch
                    chunks.append(current_chunk.strip())
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n" + para
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def process_and_output(self, text: Any) -> str:
        """
        Processes the text and returns the chunks in the requested format (json or excel/csv).
        """
        chunks = self.split_text(text)

        result: Dict[str, Any] = {
            "total_chunks": len(chunks),
            "chunks": [{"index": i + 1, "content": chunk} for i, chunk in enumerate(chunks)]
        }

        if self.mode == "excel":
            # Returning a simulated CSV/Excel format as string
            header = "Index,Content"
            rows = [f'{item["index"]},"{item["content"].replace("\"", "\"\"")}"' for item in result["chunks"]]
            return header + "\n" + "\n".join(rows) if rows else header
        else:
            return json.dumps(result, ensure_ascii=False)


def main():
    parser = argparse.ArgumentParser(description="Long Response Chunk Splitter CLI")
    # Zero parameter one-click execution: we provide sensible defaults
    parser.add_argument("--text", type=str, default="这是一个默认的长文本示例。它将被切分成多个卡片以便阅读。支持脏数据自愈和零参数启动。", help="Text to split (optional)")
    parser.add_argument("--mode", type=str, choices=["json", "excel"], default="json", help="Output mode (optional)")
    parser.add_argument("--max-length", type=int, default=1000, help="Max length of each chunk (optional)")

    args = parser.parse_args()

    splitter = LongResponseChunkSplitter(mode=args.mode, max_length=args.max_length)
    output = splitter.process_and_output(args.text)
    print(output)

if __name__ == "__main__":  # pragma: no cover
    main()
