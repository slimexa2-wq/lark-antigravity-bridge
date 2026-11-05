import re
from typing import List, Dict, Any, Union

class LongResponseChunkSplitterAuditTrace:
    def __init__(self, max_chunk_size: int = 2000):
        # Fallback for invalid max_chunk_size
        if not isinstance(max_chunk_size, int) or max_chunk_size <= 0:
            self.max_chunk_size = 2000
        else:
            self.max_chunk_size = max_chunk_size

    def _create_trace_entry(self, step: str, original: Any, modified: Any, reason: str) -> Dict[str, Any]:
        return {
            "step": step,
            "original_length": len(str(original)) if original is not None else 0,
            "modified_length": len(str(modified)) if modified is not None else 0,
            "diff_highlight": f"Changed from '{str(original)[:50]}...' to '{str(modified)[:50]}...'" if original != modified else "No change",
            "reason": reason
        }

    def split_and_trace(self, text: Any, custom_max_chunk_size: int = None) -> Dict[str, Any]:
        audit_trace = []

        # 1. Parameter fallback and self-healing for max_chunk_size
        current_max_size = self.max_chunk_size
        if custom_max_chunk_size is not None:
            if not isinstance(custom_max_chunk_size, int) or custom_max_chunk_size <= 0:
                audit_trace.append(self._create_trace_entry(
                    "param_healing",
                    custom_max_chunk_size,
                    self.max_chunk_size,
                    "Invalid custom_max_chunk_size provided; fallback to default."
                ))
            else:
                current_max_size = custom_max_chunk_size

        # 2. Dirty data self-healing for text
        original_text = text
        if text is None:
            text = ""
            audit_trace.append(self._create_trace_entry("data_healing", original_text, text, "Input was None; converted to empty string."))
        elif not isinstance(text, str):
            text = str(text)
            audit_trace.append(self._create_trace_entry("data_healing", original_text, text, "Input was not a string; casted to string."))

        # 3. Data deduplication and whitespace normalization
        pre_clean_text = text
        # Remove excessive blank lines (more than 2 to just 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        # Strip leading/trailing whitespaces
        text = text.strip()
        if pre_clean_text != text:
            audit_trace.append(self._create_trace_entry(
                "whitespace_normalization",
                pre_clean_text,
                text,
                "Removed excessive blank lines and stripped leading/trailing spaces for clean frontend display."
            ))

        # 4. Semantic splitting
        chunks = []
        if not text:
            audit_trace.append(self._create_trace_entry("split_execution", text, [], "Text is empty; returning empty chunks."))
            return {"chunks": chunks, "audit_trace": audit_trace}

        paragraphs = text.split('\n\n')
        current_chunk = ""

        for i, para in enumerate(paragraphs):
            # If a single paragraph is longer than max size, we must force split it by lines or words
            if len(para) > current_max_size:
                audit_trace.append(self._create_trace_entry(
                    "extreme_boundary_handling",
                    para,
                    "<split_sub_paragraphs>",
                    f"Paragraph {i} length ({len(para)}) exceeds max size ({current_max_size}); applying forced line/char splitting."
                ))

                # If current_chunk is not empty, push it
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""

                # Split the long paragraph by lines first
                lines = para.split('\n')
                for line in lines:
                    if len(line) > current_max_size:
                        # Flush current_chunk before adding broken lines to preserve order
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                            current_chunk = ""

                        # Extreme extreme boundary: a single line exceeds max chunk size
                        # Force split by characters
                        for char_idx in range(0, len(line), current_max_size):
                            chunks.append(line[char_idx:char_idx + current_max_size])
                    else:
                        if len(current_chunk) + len(line) + 1 > current_max_size:
                            chunks.append(current_chunk.strip())
                            current_chunk = line
                        else:
                            current_chunk = current_chunk + "\n" + line if current_chunk else line
            else:
                # Normal paragraph fits or fits with current chunk
                separator = "\n\n" if current_chunk else ""
                if len(current_chunk) + len(separator) + len(para) > current_max_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    current_chunk = current_chunk + separator + para

        if current_chunk:
            chunks.append(current_chunk.strip())

        audit_trace.append(self._create_trace_entry(
            "split_execution_complete",
            f"<Total {len(paragraphs)} paragraphs>",
            f"<Total {len(chunks)} chunks>",
            "Successfully split text into chunks based on semantic boundaries (paragraphs/lines) and length limits."
        ))

        return {
            "chunks": chunks,
            "audit_trace": audit_trace
        }
