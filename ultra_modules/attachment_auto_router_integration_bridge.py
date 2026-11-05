import re
import json

class AttachmentAutoRouter:
    """
    Attachment Auto Router Integration Bridge.
    Automatically identifies the business type of attachments based on filenames/content
    and routes them to the appropriate engine (周报, 提成, 标书, 漫剧).
    Features include silent schema migration and dirty data self-healing.
    """

    def __init__(self):
        self.engine_mapping = {
            "weekly_report": "周报引擎",
            "commission": "提成引擎",
            "bidding": "标书引擎",
            "comic": "漫剧引擎"
        }
        self.default_engine = "unknown"

    def route_attachment(self, filename: str, content: str = "", metadata: dict = None) -> dict:
        """
        Frontend integration method: Zero-configuration, silent automatic mapping.
        """
        if metadata is None:
            metadata = {}

        # Self-healing for dirty data: normalize string inputs
        filename = str(filename).strip() if filename else ""
        content = str(content).strip() if content else ""

        # Ensure metadata is a dictionary
        if not isinstance(metadata, dict):
            metadata = {}

        # 1. Identify Business Type
        engine_key = self._identify_engine(filename, content)

        # 2. Schema Forward Compatibility Mapping
        migrated_metadata = self._migrate_schema(engine_key, metadata)

        result = {
            "status": "success",
            "routed_engine": self.engine_mapping.get(engine_key, "未匹配"),
            "engine_key": engine_key,
            "filename": filename,
            "metadata_version": migrated_metadata.get("version", "1.0"),
            "migrated_metadata": migrated_metadata
        }
        return result

    def _identify_engine(self, filename: str, content: str) -> str:
        """
        Heuristic-based engine identification.
        """
        lower_filename = filename.lower()
        lower_content = content.lower()

        if "周报" in lower_filename or "weekly" in lower_filename:
            return "weekly_report"
        if "提成" in lower_filename or "commission" in lower_filename or "绩效" in lower_filename:
            return "commission"
        if "标书" in lower_filename or "bidding" in lower_filename or "招标" in lower_filename:
            return "bidding"
        if "漫剧" in lower_filename or "comic" in lower_filename or "剧本" in lower_filename:
            return "comic"

        # Content based heuristic as fallback
        if "完成工作" in lower_content or "下周计划" in lower_content:
            return "weekly_report"
        if "提成点" in lower_content or "销售额" in lower_content:
            return "commission"
        if "资质要求" in lower_content or "投标总价" in lower_content:
            return "bidding"
        if "分镜" in lower_content or "剧集" in lower_content:
            return "comic"

        return self.default_engine

    def _migrate_schema(self, engine_key: str, metadata: dict) -> dict:
        """
        Automatic schema forward compatibility converter.
        Silently maps legacy fields to new fields without manual configuration.
        """
        migrated = metadata.copy()

        # Check current version, default to legacy if not specified
        version = str(migrated.get("version", "legacy")).lower()

        if engine_key == "weekly_report":
            if "last_week_done" in migrated:
                migrated["accomplishments"] = migrated.pop("last_week_done")
            if "next_week_todo" in migrated:
                migrated["plan"] = migrated.pop("next_week_todo")
            migrated["version"] = "2.0"

        elif engine_key == "commission":
            if "sales_volume" in migrated:
                migrated["total_sales"] = migrated.pop("sales_volume")
            if "rate" in migrated:
                migrated["commission_rate"] = migrated.pop("rate")
            migrated["version"] = "2.0"

        elif engine_key == "bidding":
            if "price" in migrated:
                migrated["total_bid_amount"] = migrated.pop("price")
            migrated["version"] = "2.0"

        elif engine_key == "comic":
            if "episode_count" in migrated:
                migrated["total_episodes"] = migrated.pop("episode_count")
            migrated["version"] = "2.0"

        else:
            migrated["version"] = "1.0"

        # Global normalizations
        if "author_name" in migrated and "author" not in migrated:
            migrated["author"] = migrated.pop("author_name")

        return migrated
