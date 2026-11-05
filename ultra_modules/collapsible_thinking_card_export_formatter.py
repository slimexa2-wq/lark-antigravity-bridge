import math

def build_card_and_report(conclusion=None, reasoning=None, metrics=None):
    """
    Builds a Lark V2 card with collapsible reasoning, conclusion at the top,
    and an undo action button. Also generates a 3-line plain text summary,
    and sanitizes metrics data.
    """
    # Default fallbacks
    conclusion = conclusion or "No conclusion provided."
    reasoning = reasoning or "No reasoning provided."
    metrics = metrics or {}

    # Clean dirty data in metrics
    cleaned_metrics = {}
    for k, v in metrics.items():
        if v is None:
            cleaned_metrics[k] = 0
        elif isinstance(v, (int, float)) and math.isnan(v):
            cleaned_metrics[k] = 0.0
        else:
            cleaned_metrics[k] = v

    # Build Lark Card V2
    card = {
        "schema": "2.0",
        "header": {
            "title": {
                "content": "Reasoning & Conclusion",
                "tag": "plain_text"
            },
            "template": "blue"
        },
        "body": {
            "direction": "column",
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"**Conclusion:**\n{conclusion}"
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "collapsible_panel",
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": "Reasoning Process (Click to expand)"
                        }
                    },
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": reasoning
                        }
                    ]
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "tag": "plain_text",
                                "content": "Undo"
                            },
                            "type": "danger",
                            "value": {
                                "action": "undo"
                            }
                        }
                    ]
                }
            ]
        }
    }

    # Generate 3-line plain text report
    conclusion_summary = conclusion.split('\n')[0][:50]
    reasoning_summary = reasoning.split('\n')[0][:50]
    metrics_str = ", ".join([f"{k}: {v}" for k, v in cleaned_metrics.items()])
    if not metrics_str:
        metrics_str = "None"

    report = f"Conclusion: {conclusion_summary}\nReasoning: {reasoning_summary}\nMetrics: {metrics_str}"

    return {
        "card": card,
        "report": report,
        "comments": 0,
        "metrics": cleaned_metrics
    }
