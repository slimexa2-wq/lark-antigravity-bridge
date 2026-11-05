import json

class RateLimitExplainer:
    @staticmethod
    def explain(total_requests=0, success=0, queued=0, dropped=0, rate_limited_429=0):
        # Default fallback for missing/None parameters
        total_requests = total_requests if total_requests is not None else 0
        success = success if success is not None else 0
        queued = queued if queued is not None else 0
        dropped = dropped if dropped is not None else 0
        rate_limited_429 = rate_limited_429 if rate_limited_429 is not None else 0

        # Self-healing dirty data (convert negative to 0)
        total_requests = max(0, total_requests)
        success = max(0, success)
        queued = max(0, queued)
        dropped = max(0, dropped)
        rate_limited_429 = max(0, rate_limited_429)

        # Determine overall state
        state = "Normal"
        if dropped > 0:
            state = "Critical - Dropping Messages"
        elif queued > 0:
            state = "Warning - Queuing Messages"
        elif rate_limited_429 > 0:
            state = "Warning - Encountered 429 Limits"

        # Construct Plain English Summary
        summary_sentences = []
        if state == "Normal":
            summary_sentences.append("All systems operational.")
            if total_requests > 0:
                summary_sentences.append(f"Successfully processed {success} out of {total_requests} requests.")
        else:
            if rate_limited_429 > 0:
                summary_sentences.append(f"Encountered {rate_limited_429} rate limit (429) events from Feishu API.")
            if queued > 0:
                summary_sentences.append(f"{queued} messages are currently queued for retry to ensure smooth delivery.")
            if dropped > 0:
                summary_sentences.append(f"CRITICAL: {dropped} messages had to be dropped due to exceeding queue limits.")
            if success > 0:
                summary_sentences.append(f"Despite issues, {success} messages were successfully delivered.")

        plain_text = " ".join(summary_sentences)

        # Markdown representation
        markdown = f"""## Rate Limit Report: {state}

**Summary:** {plain_text}

### Details:
- **Total Requests:** {total_requests}
- **Successfully Delivered:** {success}
- **Currently Queued:** {queued}
- **Dropped Messages:** {dropped}
- **429 Rate Limits Hit:** {rate_limited_429}
"""

        # HTML representation
        html_color = "green" if state == "Normal" else ("red" if "Critical" in state else "orange")
        html = f"""<div style="border: 1px solid {html_color}; padding: 10px; border-radius: 5px; font-family: sans-serif;">
  <h2 style="color: {html_color}; margin-top: 0;">Rate Limit Report: {state}</h2>
  <p style="font-weight: bold;">{plain_text}</p>
  <ul style="list-style-type: none; padding-left: 0;">
    <li><span style="font-weight: bold;">Total Requests:</span> {total_requests}</li>
    <li><span style="font-weight: bold;">Successfully Delivered:</span> {success}</li>
    <li><span style="font-weight: bold;">Currently Queued:</span> {queued}</li>
    <li><span style="font-weight: bold; color: {'red' if dropped > 0 else 'black'};">Dropped Messages:</span> {dropped}</li>
    <li><span style="font-weight: bold; color: {'orange' if rate_limited_429 > 0 else 'black'};">429 Rate Limits Hit:</span> {rate_limited_429}</li>
  </ul>
</div>"""

        # JSON representation
        json_data = {
            "state": state,
            "summary": plain_text,
            "metrics": {
                "total_requests": total_requests,
                "success": success,
                "queued": queued,
                "dropped": dropped,
                "rate_limited_429": rate_limited_429
            }
        }

        return {
            "markdown": markdown,
            "html": html,
            "json": json_data,
            "plain_text": plain_text
        }
