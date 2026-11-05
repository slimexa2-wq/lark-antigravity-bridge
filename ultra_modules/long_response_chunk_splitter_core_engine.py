import re
from typing import List, Any

def split_long_response(text: Any, max_chunk_size: int = 30000) -> List[str]:
    """
    Zero-configuration semantic chunk splitter for ultra-long responses.
    Splits text by semantic boundaries (headings, paragraphs, sentences)
    to ensure coherent reading experience on platforms like Lark/Feishu.
    """
    # 1. Dirty data silent cleaning
    if text is None:
        return []

    if not isinstance(text, str):
        try:
            text = str(text)
        except Exception:
            return []

    if not text:
        return []

    # 2. Missing parameter fallback / boundary conditions
    if not isinstance(max_chunk_size, int) or max_chunk_size <= 0:
        max_chunk_size = 30000

    if len(text) <= max_chunk_size:
        return [text]

    chunks = []

    while text:
        if len(text) <= max_chunk_size:
            chunks.append(text)
            break

        candidate = text[:max_chunk_size]
        split_pos = -1

        # Priority 1: Markdown Headings (split before the heading)
        for heading in ['\n# ', '\n## ', '\n### ', '\n#### ']:
            pos = candidate.rfind(heading)
            if pos > 0:
                split_pos = max(split_pos, pos)

        if split_pos != -1:
            chunks.append(text[:split_pos])
            text = text[split_pos:]
            continue

        # Priority 2: Paragraph breaks
        pos = candidate.rfind('\n\n')
        if pos > 0:
            split_pos = pos + 2
            chunks.append(text[:split_pos])
            text = text[split_pos:]
            continue

        # Priority 3: Line breaks
        pos = candidate.rfind('\n')
        if pos > 0:
            split_pos = pos + 1
            chunks.append(text[:split_pos])
            text = text[split_pos:]
            continue

        # Priority 4: Sentence ends
        sentence_end_match = None
        for match in re.finditer(r'[。！？.!?]+', candidate):
            if match.end() > 0 and match.end() < max_chunk_size:
                sentence_end_match = match

        if sentence_end_match:
            split_pos = sentence_end_match.end()
            chunks.append(text[:split_pos])
            text = text[split_pos:]
            continue

        # Priority 5: Sub-sentence/Phrase ends
        phrase_end_match = None
        for match in re.finditer(r'[；;，,]+', candidate):
            if match.end() > 0 and match.end() < max_chunk_size:
                phrase_end_match = match

        if phrase_end_match:
            split_pos = phrase_end_match.end()
            chunks.append(text[:split_pos])
            text = text[split_pos:]
            continue

        # Priority 6: Word boundary (space)
        pos = candidate.rfind(' ')
        if pos > 0:
            split_pos = pos + 1
            chunks.append(text[:split_pos])
            text = text[split_pos:]
            continue

        # Priority 7: Hard split (fallback)
        split_pos = max_chunk_size
        chunks.append(text[:split_pos])
        text = text[split_pos:]

    return chunks
