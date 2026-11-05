import json
import math
import statistics
import logging
from typing import List, Dict, Any, Union, Optional

class PartialMarkdownHealerAnomalyRadar:
    """
    A unified healer and anomaly radar module for handling partial markdown
    and detecting anomalies silently in the background while keeping the
    frontend clean and zero-configuration.
    """
    def __init__(self, fallback_default: Any = None):
        self.fallback_default = fallback_default if fallback_default is not None else {}
        self.logger = logging.getLogger(__name__)
        # Prevent logger from printing to stdout unless specifically configured
        self.logger.addHandler(logging.NullHandler())

    def heal_markdown(self, content: Optional[str]) -> str:
        """
        Silently fixes incomplete markdown elements like code blocks, tables, and bold text.
        """
        if not content:
            return ""

        healed_content = content

        # Heal bold text: check if odd number of '**'
        if healed_content.count('**') % 2 != 0:
            healed_content += '**'

        # Heal code blocks: check if odd number of '```'
        if healed_content.count('```') % 2 != 0:
            if not healed_content.endswith('\n'):
                healed_content += '\n'
            healed_content += '```'

        # Heal tables: if there's a '|' but not closed properly at the end of the line
        lines = healed_content.split('\n')
        if lines:
            last_line = lines[-1].strip()
            if '|' in last_line and not last_line.endswith('|'):
                lines[-1] = last_line + ' |'
                healed_content = '\n'.join(lines)

        return healed_content

    def heal_json(self, content: Optional[str]) -> Any:
        """
        Parses JSON. If incomplete/truncated, attempts to append missing brackets/braces/quotes.
        Returns fallback default dict if healing fails (missing parameter fallback/dirty data).
        """
        if not content:
            return self.fallback_default

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Attempt to heal using a simple stack
        healed_content = content.strip()
        stack = []
        in_string = False
        escaped = False

        for char in healed_content:
            if not in_string:
                if char == '"':
                    in_string = True
                elif char == '{':
                    stack.append('}')
                elif char == '[':
                    stack.append(']')
                elif char in ('}', ']'):
                    if stack and stack[-1] == char:
                        stack.pop()
                    else:
                        # Unmatched closing brace/bracket, maybe malformed earlier
                        # We just continue and let the parser fail later
                        pass
            else:
                if char == '\\' and not escaped:
                    escaped = True
                elif char == '"' and not escaped:
                    in_string = False
                else:
                    escaped = False

        if in_string:
            healed_content += '"'

        # Pop all remaining open structures from stack and append them
        while stack:
            healed_content += stack.pop()

        try:
            return json.loads(healed_content)
        except json.JSONDecodeError:
            # Fallback to defaults if we cannot parse after basic healing
            self.logger.warning("Failed to heal JSON. Falling back to default.")
            return self.fallback_default

    def scan_anomalies(self, data: List[Dict[str, Any]], value_key: str = 'value') -> List[Dict[str, Any]]:
        """
        Scans a list of dictionaries for anomalies based on a numeric key.
        Uses Z-Score to highlight the top 3% anomalies (Red with reason),
        and passes 97% normal items (Green/Yellow silently).
        Provides zero-configuration fault tolerance for missing keys/empty data.
        """
        if not data:
            return []

        # Extract numeric values
        values = []
        for item in data:
            val = item.get(value_key)
            if isinstance(val, (int, float)):
                values.append(val)

        if not values or len(values) < 2:
            # Not enough data for stats, just mark all green
            for item in data:
                item['radar_status'] = 'Green'
                item['radar_reason'] = 'Normal (insufficient data for anomaly detection)'
            return data

        mean = statistics.mean(values)
        stdev = statistics.pstdev(values)

        if stdev == 0:
            # All values are the same
            for item in data:
                item['radar_status'] = 'Green'
                item['radar_reason'] = 'Normal'
            return data

        # We want to flag the top 3% extreme values.
        # Assuming a normal distribution, a Z-score > ~2.17 corresponds to top 1.5% and < -2.17 to bottom 1.5% (total 3% two-tailed).
        # Or, we can simply sort and take the top 3% mathematically if we want strict percentile.
        # Since the requirement says "Z-Score/IQR", let's use Z-score as a continuous metric.
        # A Z-score threshold of roughly 2.17 captures ~3% anomalies on a perfect normal curve.
        Z_THRESHOLD = 2.17

        for item in data:
            val = item.get(value_key)
            if isinstance(val, (int, float)):
                z_score = abs((val - mean) / stdev)
                if z_score > Z_THRESHOLD:
                    item['radar_status'] = 'Red'
                    item['radar_reason'] = f'Anomaly detected: value deviates significantly (Z-Score: {z_score:.2f}) from the average.'
                else:
                    item['radar_status'] = 'Green' if z_score < 1.0 else 'Yellow'
                    item['radar_reason'] = 'Normal'
            else:
                # Handle dirty data / missing parameter fallback
                item['radar_status'] = 'Green'
                item['radar_reason'] = 'Normal (non-numeric or missing value)'

        return data
