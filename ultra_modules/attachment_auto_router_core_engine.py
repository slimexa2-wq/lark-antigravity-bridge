from typing import Optional, Dict, Any
import re

def route_attachment(file_name: Optional[str] = None, file_content: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
    """
    Routes an attachment to the correct engine based on its name, content, and metadata.

    Engines:
    - WEEKLY_REPORT_ENGINE: matches "周报", "weekly", "汇报"
    - COMMISSION_ENGINE: matches "提成", "commission", "奖金"
    - BIDDING_ENGINE: matches "标书", "bidding", "投标"
    - COMIC_ENGINE: matches "漫剧", "comic", "漫画"
    - UNKNOWN_ENGINE: default fallback
    """
    # 1. Parameter fallback & Dirty data sanitization
    if file_name is None or not isinstance(file_name, str):
        file_name = ""
    if file_content is None or not isinstance(file_content, str):
        file_content = ""
    if metadata is None or not isinstance(metadata, dict):
        metadata = {}

    # Strip and lower
    file_name = file_name.strip().lower()
    file_content = file_content.strip().lower()

    # 2. Extract possible text signals
    # We search the filename primarily, but also fallback to file_content and metadata if needed.
    search_text = f"{file_name} {file_content}"

    # Try to extract from metadata if there is a 'description' or 'title'
    if 'title' in metadata and isinstance(metadata['title'], str):
        search_text += f" {metadata['title'].lower()}"
    if 'description' in metadata and isinstance(metadata['description'], str):
        search_text += f" {metadata['description'].lower()}"

    # 3. Routing Rules

    # Priority could be defined based on strict matches in title first, but we can do a general search.

    if re.search(r'周报|weekly|汇报|report', search_text):
        return "WEEKLY_REPORT_ENGINE"

    if re.search(r'提成|commission|奖金|bonus', search_text):
        return "COMMISSION_ENGINE"

    if re.search(r'标书|bidding|投标|bid', search_text):
        return "BIDDING_ENGINE"

    if re.search(r'漫剧|comic|漫画|manga|anime', search_text):
        return "COMIC_ENGINE"

    return "UNKNOWN_ENGINE"
