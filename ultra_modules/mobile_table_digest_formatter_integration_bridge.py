import datetime
import json
import logging

class MobileTableDigestFormatter:
    """
    Bridge module for zero-configuration, self-healing Mobile Table Digest formatting.
    Transforms wide tables into 3-line summaries with anomaly highlights and attachment cards.
    Handles auto-mapping of V1/V2 schemas.
    """
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def _clean_and_map_data(self, item: dict, kwargs: dict) -> dict:
        """
        Cleans data (strings to floats/ints) and maps V1 schemas to V2.
        Fills missing fields with sensible defaults (0 or 'unknown').
        """
        if not isinstance(item, dict):
            return {}

        mapped = {}

        # ID Mapping
        mapped_id = item.get('id') or item.get('item_id') or item.get('v1_id')
        mapped['id'] = str(mapped_id) if mapped_id is not None else 'unknown_id'

        # Name Mapping
        mapped_name = item.get('name') or item.get('title') or item.get('v1_name')
        mapped['name'] = str(mapped_name) if mapped_name is not None else 'unknown_item'

        # Date Mapping
        mapped_date = item.get('date') or item.get('created_at') or item.get('v1_date')
        if mapped_date:
            try:
                # Basic string cleaning
                mapped['date'] = str(mapped_date).strip()
            except Exception:
                mapped['date'] = '1970-01-01'
        else:
             mapped['date'] = '1970-01-01'

        # Amount Mapping (e.g. amount -> total_amount)
        raw_amount = item.get('total_amount')
        if raw_amount is None:
             raw_amount = item.get('amount')
        if raw_amount is None:
             raw_amount = item.get('v1_amount')

        mapped['total_amount'] = self._to_float(raw_amount, kwargs.get('default_amount', 0.0))

        # Status Mapping
        mapped_status = item.get('status') or item.get('state') or item.get('v1_status')
        mapped['status'] = str(mapped_status).lower() if mapped_status is not None else kwargs.get('default_status', 'pending')

        return mapped

    def _to_float(self, value, default_val=0.0):
        if value is None:
            return default_val
        try:
            if isinstance(value, str):
                value = value.replace(',', '').replace('$', '').strip()
            return float(value)
        except (ValueError, TypeError):
            return default_val

    def _detect_anomalies(self, items: list, kwargs: dict) -> list:
        """
        Detects anomalies based on thresholds or status.
        """
        anomalies = []
        high_threshold = kwargs.get('anomaly_high_threshold', 10000.0)

        for item in items:
            amount = item.get('total_amount', 0.0)
            status = item.get('status', '')

            reasons = []
            if amount < 0:
                reasons.append("Negative amount")
            if amount > high_threshold:
                reasons.append(f"Amount exceeds {high_threshold}")
            if status in ['failed', 'error', 'rejected', 'abnormal']:
                reasons.append(f"Abnormal status: {status}")

            if reasons:
                anomalies.append({
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'reasons': reasons,
                    'amount': amount
                })

        return anomalies

    def format_mobile_table_digest(self, raw_data: list, **kwargs) -> dict:
        """
        Main entry point. Processes raw_data and returns 3-line digest + card metadata.
        Zero-config, fault-tolerant.
        """
        if raw_data is None:
            raw_data = []
        if not isinstance(raw_data, list):
            # Attempt recovery if a dict is passed instead of list
            if isinstance(raw_data, dict):
                raw_data = [raw_data]
            else:
                raw_data = []

        mapped_items = []
        for item in raw_data:
            try:
                clean_item = self._clean_and_map_data(item, kwargs)
                if clean_item:
                    mapped_items.append(clean_item)
            except Exception:
                # Silently ignore unparseable items
                pass

        total_items = len(mapped_items)
        total_sum = sum(item.get('total_amount', 0.0) for item in mapped_items)

        anomalies = self._detect_anomalies(mapped_items, kwargs)
        anomaly_count = len(anomalies)

        # 3-line digest generation
        line1 = f"📊 Summary: {total_items} items processed, Total Value: {total_sum:,.2f}"

        if anomaly_count > 0:
            line2 = f"⚠️ Anomalies Detected: {anomaly_count} items require attention!"
        else:
            line2 = "✅ All items appear normal."

        if kwargs.get('include_date', True):
            current_date = kwargs.get('report_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            line3 = f"📅 Report Date: {current_date}"
        else:
            line3 = "💡 Action: Tap card to download full details."

        digest = f"{line1}\n{line2}\n{line3}"

        # Attachment Card Metadata
        card_metadata = {
            "type": "attachment_card",
            "title": kwargs.get('card_title', "Data Table Export"),
            "file_type": kwargs.get('file_type', "xlsx"),
            "download_url": kwargs.get('download_url', "https://example.com/download/default.xlsx"),
            "anomalies_highlight": anomalies
        }

        return {
            "digest_text": digest,
            "card_metadata": card_metadata,
            "metrics": {
                "total_items": total_items,
                "total_sum": total_sum,
                "anomaly_count": anomaly_count
            }
        }
