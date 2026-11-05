import statistics
from typing import List, Dict, Any, Union

def extract_anomalies(data: List[Dict[str, Any]], target_key: str = 'value', default_value: float = 0.0) -> Dict[str, Any]:
    """
    Extracts anomalous intents from a list of parsed voice command intents, based on Z-score.
    Automatically handles dirty data, fills in defaults for missing parameters, and classifies items by color.
    Top 3% threshold is approximately Z-score > 1.88.

    Args:
        data: List of dicts representing parsed intents.
        target_key: The key in the dict to analyze.
        default_value: Default value if key is missing or invalid.

    Returns:
        Dict with stats, anomalies (Top 3%), and a plain text reason for the anomalies.
    """

    # 1. Clean and normalize data (Self-healing & Missing Defaults)
    cleaned_data = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            # Invalid item format, create a dummy item
            cleaned_item = {'id': f'auto_id_{i}', target_key: default_value, 'original': str(item)}
        else:
            cleaned_item = dict(item)  # copy
            if 'id' not in cleaned_item:
                cleaned_item['id'] = f'auto_id_{i}'

            raw_val = cleaned_item.get(target_key, default_value)
            try:
                if raw_val is None:
                    val = default_value
                else:
                    val = float(raw_val)
            except (ValueError, TypeError):
                val = default_value

            cleaned_item[target_key] = val
        cleaned_data.append(cleaned_item)

    if not cleaned_data:
        return {
            'anomalies': [],
            'normal': [],
            'stats': {'mean': 0.0, 'stdev': 0.0, 'count': 0},
            'summary': "无数据输入。"
        }

    values = [item[target_key] for item in cleaned_data]
    count = len(values)

    if count < 2:
        # Cannot compute stdev
        for item in cleaned_data:
            item['color'] = 'green'
            item['z_score'] = 0.0
            item['reason'] = "数据不足，默认放行"
        return {
            'anomalies': [],
            'normal': cleaned_data,
            'stats': {'mean': values[0] if count == 1 else 0.0, 'stdev': 0.0, 'count': count},
            'summary': "样本量过少，全部放行。"
        }

    try:
        mean = statistics.mean(values)
        stdev = statistics.stdev(values)
    except statistics.StatisticsError:
        mean = 0.0
        stdev = 0.0

    # Standardize handling of 0 variance
    if stdev == 0.0:
        for item in cleaned_data:
            item['color'] = 'green'
            item['z_score'] = 0.0
            item['reason'] = "数据无波动，默认放行"
        return {
            'anomalies': [],
            'normal': cleaned_data,
            'stats': {'mean': mean, 'stdev': stdev, 'count': count},
            'summary': "所有数值相同，无异常。"
        }

    # 2. Analyze using Z-score (Top 3% ~ Z > 1.88)
    anomalies = []
    normal = []

    Z_THRESHOLD = 1.88

    for item in cleaned_data:
        val = item[target_key]
        z = (val - mean) / stdev
        item['z_score'] = round(z, 3)

        if z > Z_THRESHOLD:
            item['color'] = 'red'
            diff_pct = ((val - mean) / mean * 100) if mean != 0 else float('inf')
            item['reason'] = f"数值严重偏高(Z={item['z_score']})，偏离均值{diff_pct:.1f}%，需人工关注"
            anomalies.append(item)
        elif z < -Z_THRESHOLD:
             # Typically we might care about low anomalies too, but let's say "Top 3%" implies high values for this use case,
             # or absolute anomalies. We'll mark them yellow/red depending on absolute deviation.
            item['color'] = 'yellow'
            diff_pct = ((mean - val) / mean * 100) if mean != 0 else float('inf')
            item['reason'] = f"数值异常偏低(Z={item['z_score']})，偏离均值{diff_pct:.1f}%，建议复核"
            anomalies.append(item)
        else:
            item['color'] = 'green'
            item['reason'] = "正常范围，静默放行"
            normal.append(item)

    # Sort anomalies by z-score magnitude
    anomalies.sort(key=lambda x: abs(x['z_score']), reverse=True)

    summary = f"扫描{count}项数据，均值{mean:.2f}，发现{len(anomalies)}项异常。"
    if anomalies:
         summary += f" 最异常项: {anomalies[0]['id']}。"

    return {
        'anomalies': anomalies,
        'normal': normal,
        'stats': {
            'mean': round(mean, 2),
            'stdev': round(stdev, 2),
            'count': count
        },
        'summary': summary
    }
