import time
import datetime
import random
import uuid

def format_mobile_table_digest(data=None, **kwargs):
    """
    Feishu mobile wide table digest formatter.
    Features: One-click direct access, zero confirmation, zero configuration, auto fallback.
    Returns: 3 lines of core digest, highlights anomalies, and attachment download card.
    """
    # Missing parameter auto fallback
    if data is None:
        data = []
    if not isinstance(data, list):
        data = [data]

    # Dirty data self-healing: ensure elements are dicts
    clean_data = []
    for row in data:
        if isinstance(row, dict):
            clean_data.append(row)
        else:
            # Fallback for non-dict
            clean_data.append({"_raw": str(row)})

    # Extract 3 lines of core digest (e.g., top 3 rows or specific key metrics)
    # We will pick the first 3 valid items or pad with empty rows
    digest_lines = []
    anomalies = []

    for i in range(min(3, len(clean_data))):
        row = clean_data[i]
        # Example formatting: prefer 'title' or 'name', fallback to first value
        title = row.get("title", row.get("name", "Unnamed Item"))
        value = row.get("value", row.get("amount", "0"))

        # Highlight anomalies (e.g., negative values, missing crucial fields, extreme values)
        is_anomaly = False
        try:
            val_float = float(value)
            if val_float < 0 or val_float > 1000000:
                is_anomaly = True
        except (ValueError, TypeError):
            if str(value) == "0" and len(row) > 1:
                is_anomaly = False # Exclude zero values
            else:
                is_anomaly = True # Unparseable value usually implies anomaly if not fallback

        line = f"Item: {title} | Value: {value}"
        if is_anomaly:
            line = f"⚠️ [ANOMALY] {line}"
            anomalies.append(row)

        digest_lines.append(line)

    # If less than 3 lines, pad with defaults
    while len(digest_lines) < 3:
        digest_lines.append("- Empty Slot -")

    # Generate attachment download card
    download_card = {
        "type": "attachment",
        "title": "Complete Table Data",
        "action": "Download",
        "url": "https://feishu.example.com/api/download/table", # Default sensible fallback
        "rows_count": len(clean_data)
    }

    # Format output
    output = "--- Mobile Digest ---\n"
    output += "\n".join(digest_lines)
    output += "\n\n"
    if anomalies:
        output += f"Detected {len(anomalies)} anomalies. Please review carefully.\n"
    output += f"[Attachment Card] {download_card['title']} ({download_card['rows_count']} rows) - {download_card['url']}"

    return output


def generate_synthetic_fixtures(num_rows=10000):
    """
    Constructs synthetic dataset with nulls, garbled text, massive concurrency, cross-year/month boundaries.
    """
    fixtures = []

    # Pre-defined chaos
    garbled = ["锟斤拷", "", "\x00\x01\x02", "null", "NaN"]

    for _ in range(num_rows):
        chaos_type = random.random()

        if chaos_type < 0.05:
            # Nulls and missing
            fixtures.append({})
        elif chaos_type < 0.10:
            # Garbled text
            fixtures.append({
                "title": random.choice(garbled),
                "value": random.choice(garbled)
            })
        elif chaos_type < 0.15:
            # Cross year/month boundaries
            fixtures.append({
                "title": "Year End Report",
                "value": "9999999",
                "date": "2023-12-31T23:59:59Z"
            })
            fixtures.append({
                "title": "New Year Kickoff",
                "value": "-100",
                "date": "2024-01-01T00:00:01Z"
            })
        elif chaos_type < 0.20:
            # Wrong types
            fixtures.append("Just a string instead of dict")
        else:
            # Normal data
            fixtures.append({
                "title": f"Task {uuid.uuid4().hex[:8]}",
                "value": str(random.randint(10, 1000)),
                "date": datetime.datetime.now().isoformat()
            })

    return fixtures


def run_performance_benchmark():
    """
    Verifies ms-level response and zero crashes with large synthetic dataset.
    """
    dataset = generate_synthetic_fixtures(10000)

    start_time = time.time()
    try:
        result = format_mobile_table_digest(dataset)
    except Exception as e:
        return False, f"Crash detected: {str(e)}", 0

    end_time = time.time()
    duration_ms = (end_time - start_time) * 1000

    if duration_ms > 500: # 500ms max
        return False, f"Performance too slow: {duration_ms:.2f}ms", duration_ms

    return True, "Success", duration_ms
