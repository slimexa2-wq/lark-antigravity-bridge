import re
import copy
from typing import List, Dict, Any, Optional

class SchemaVersionConverter:
    """
    Silently maps various old schema fields to the unified modern schema.
    Auto-cleans dirty data, handles missing defaults, and ensures robust fault tolerance.
    """
    @staticmethod
    def forward_compatible_convert(raw_data: Any) -> Dict[str, Any]:
        # Handle dirty or invalid data types silently
        if not isinstance(raw_data, dict):
            raw_data = {"text": str(raw_data) if raw_data is not None else ""}

        converted = copy.deepcopy(raw_data)

        # Unify text content mapping
        if "text" not in converted or not converted["text"]:
            text_candidates = ["msg", "body", "content", "message"]
            for candidate in text_candidates:
                if converted.get(candidate):
                    converted["text"] = str(converted[candidate])
                    break

        # Ensure text is at least an empty string to avoid crashes
        if "text" not in converted or converted["text"] is None:
            converted["text"] = ""
        elif not isinstance(converted["text"], str):
            converted["text"] = str(converted["text"])

        # Unify title mapping
        if "title" not in converted or not converted["title"]:
            title_candidates = ["header", "subject", "topic"]
            for candidate in title_candidates:
                if converted.get(candidate):
                    converted["title"] = str(converted[candidate])
                    break

        # Provide reasonable defaults
        if "title" not in converted or converted["title"] is None:
            converted["title"] = "Ultra Report"
        elif not isinstance(converted["title"], str):
            converted["title"] = str(converted["title"])

        return converted

class LongResponseChunkSplitterIntegrationBridge:
    """
    Splits extra-long reports by semantic boundaries into cohesive Feishu Card structures.
    Guarantees zero crashes and responsiveness even with extreme boundary cases.
    """
    def __init__(self, max_chunk_size: int = 2000):
        # Fallback to sensible default if provided size is invalid
        try:
            self.max_chunk_size = int(max_chunk_size)
            if self.max_chunk_size < 10:
                self.max_chunk_size = 10
        except (ValueError, TypeError):
            self.max_chunk_size = 2000

        self.schema_converter = SchemaVersionConverter()

    def _split_by_semantic_boundaries(self, text: str) -> List[str]:
        if not text:
            return [""]

        paragraphs = text.split('\n\n')
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para_len = len(para)
            if current_size + para_len + (2 if current_chunk else 0) > self.max_chunk_size and current_chunk:
                chunks.append('\n\n'.join(current_chunk))
                current_chunk = []
                current_size = 0

            if para_len > self.max_chunk_size:
                # Need to split this large paragraph
                # Split by sentence boundaries, keep the delimiter
                sentences = re.split(r'([。！？!?\n])', para)
                merged_sentences = []
                for i in range(0, len(sentences)-1, 2):
                    merged_sentences.append(sentences[i] + sentences[i+1])
                if len(sentences) % 2 != 0 and sentences[-1]:
                    merged_sentences.append(sentences[-1])

                for sentence in merged_sentences:
                    sen_len = len(sentence)

                    if sen_len > self.max_chunk_size:
                        # Forced hard split if a single sentence without punctuation is too large
                        if current_chunk:
                            chunks.append('\n\n'.join(current_chunk))
                            current_chunk = []
                            current_size = 0

                        # Split by max_chunk_size
                        for i in range(0, sen_len, self.max_chunk_size):
                            sub_sentence = sentence[i:i+self.max_chunk_size]
                            if len(sub_sentence) == self.max_chunk_size:
                                chunks.append(sub_sentence)
                            else:
                                current_chunk.append(sub_sentence)
                                current_size += len(sub_sentence)
                    else:
                        if current_size + sen_len > self.max_chunk_size and current_chunk:
                            chunks.append('\n\n'.join(current_chunk))
                            current_chunk = []
                            current_size = 0
                        current_chunk.append(sentence)
                        current_size += sen_len
            else:
                current_chunk.append(para)
                current_size += para_len + (2 if current_chunk else 0)

        if current_chunk:
            chunks.append('\n\n'.join(current_chunk))

        return chunks if chunks else [""]

    def process_and_bridge(self, raw_input: Any) -> List[Dict[str, Any]]:
        """
        Main entry point: Takes raw input, converts schema, splits content,
        and constructs Feishu Cards.
        """
        try:
            unified_data = self.schema_converter.forward_compatible_convert(raw_input)
            title = unified_data["title"]
            text = unified_data["text"]

            chunks = self._split_by_semantic_boundaries(text)

            feishu_cards = []
            total_chunks = len(chunks)

            for i, chunk in enumerate(chunks, 1):
                page_info = f" ({i}/{total_chunks})" if total_chunks > 1 else ""
                card = {
                    "config": {
                        "wide_screen_mode": True
                    },
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"{title}{page_info}"
                        },
                        "template": "blue"
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": chunk
                        }
                    ]
                }
                feishu_cards.append(card)

            return feishu_cards

        except Exception:
            # Absolute zero-crash guarantee fallback
            return [{
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": "Ultra Report"},
                    "template": "red"
                },
                "elements": [
                    {"tag": "markdown", "content": "Report generation encountered a soft failure, but service remains uninterrupted."}
                ]
            }]
