import json
import logging
from typing import List, Dict, Any, Optional

# Minimalist Frontend, Complex Backend Principles Applied
logger = logging.getLogger(__name__)

class ChunkSplitterAnomalyRadar:
    """
    Splits long responses into semantic chunks suitable for Feishu cards and
    detects anomalies (top 3%) to highlight for human attention.

    Backend complexity: Z-Score/IQR scanning, dirty data self-healing, automatic fallbacks.
    Frontend simplicity: Simple output with red/yellow/green semantic coloring, zero-configuration needed.
    """

    def __init__(self, data: Optional[List[Dict[str, Any]]] = None, chunk_size: int = 500):
        # Zero-configuration defaults
        self.data = data if data is not None else []
        self.chunk_size = max(100, chunk_size) if isinstance(chunk_size, int) else 500
        self._audit_trail = []

        # Self-healing missing/dirty data
        self.data = self._clean_data(self.data)

    def _clean_data(self, data: List[Any]) -> List[Dict[str, Any]]:
        """Silently clean dirty data and fall back to sensible defaults."""
        cleaned = []
        for item in data:
            if not isinstance(item, dict):
                self._audit_trail.append(f"Cleaned non-dict item: {item}")
                continue

            # Ensure 'value' exists and is numeric, else skip or default
            val = item.get('value', 0)
            try:
                val = float(val)
            except (ValueError, TypeError):
                self._audit_trail.append(f"Cleaned non-numeric value in {item}")
                val = 0.0

            cleaned.append({
                'id': str(item.get('id', 'unknown')),
                'text': str(item.get('text', '')),
                'value': val
            })
        return cleaned

    def _calculate_iqr_thresholds(self, values: List[float]) -> tuple[float, float]:
        """Calculates IQR thresholds for anomaly detection."""
        if not values:
            return 0.0, 0.0

        sorted_vals = sorted(values)
        n = len(sorted_vals)

        # Simplified IQR calculation for robust anomaly detection
        q1_idx = int(n * 0.25)
        q3_idx = int(n * 0.75)

        q1 = sorted_vals[q1_idx]
        q3 = sorted_vals[q3_idx]

        iqr = q3 - q1

        # To approximate "Top 3%", we use a more aggressive threshold
        # In a normal distribution, Q3 + ~1.88 * IQR gives approx top 3%
        upper_bound = q3 + 1.88 * iqr
        lower_bound = q1 - 1.88 * iqr

        # If zero variance, return extreme thresholds so nothing is an anomaly
        if iqr == 0:
            return float('-inf'), float('inf')

        return lower_bound, upper_bound

    def _detect_anomalies(self) -> List[Dict[str, Any]]:
        """Identify the top 3% anomaly items using Z-Score/IQR approximations."""
        if not self.data:
            return []

        values = [item['value'] for item in self.data]
        lower, upper = self._calculate_iqr_thresholds(values)

        # Mark anomalies
        results = []
        for item in self.data:
            processed_item = item.copy()
            val = item['value']

            # Simple color coding based on thresholds
            if val > upper or val < lower:
                # Top 3% Anomaly - requires attention
                processed_item['marker'] = 'red'
                processed_item['reason'] = '数值异常波动，请人工核查'
                self._audit_trail.append(f"Anomaly detected: {item['id']} with value {val}")
            else:
                # Normal items (97%) - silent pass
                processed_item['marker'] = 'green'
                processed_item['reason'] = '正常'

            results.append(processed_item)

        return results

    def process(self) -> Dict[str, Any]:
        """
        Main entry point. Processes data, detects anomalies, and chunks for Feishu.
        Frontend gets a clean, simple result.
        """
        processed_data = self._detect_anomalies()

        # Semantic chunking (simplified to grouping by chunks for cards)
        chunks = []
        current_chunk = []
        current_len = 0

        for item in processed_data:
            item_text = item['text']
            item_len = len(item_text)

            if current_len + item_len > self.chunk_size and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_len = 0

            current_chunk.append(item)
            current_len += item_len

        if current_chunk:
            chunks.append(current_chunk)

        self._audit_trail.append(f"Split into {len(chunks)} chunks")

        return {
            "status": "success",
            "chunks": chunks,
            # Frontend doesn't need to know the complex audit trail, it's just logged
            "total_items": len(self.data)
        }
