import random
import math

def calculate_next_delay(attempt=0, base_delay=1000, max_delay=60000, jitter_factor=0.5):
    """
    Calculate the next delay for exponential backoff with jitter.

    Args:
        attempt (int): The current retry attempt (0-indexed). Defaults to 0.
        base_delay (int|float): The base delay in milliseconds. Defaults to 1000.
        max_delay (int|float): The maximum delay in milliseconds. Defaults to 60000.
        jitter_factor (float): The jitter factor (0.0 to 1.0). Defaults to 0.5.

    Returns:
        float: The calculated delay in milliseconds.
    """
    # Self-healing and dirty data cleaning

    # Clean attempt
    try:
        if attempt is None or math.isnan(float(attempt)):
            attempt = 0
        else:
            attempt = int(float(attempt))
    except (TypeError, ValueError):
        attempt = 0
    attempt = max(0, attempt) # Ensure non-negative

    # Clean base_delay
    try:
        if base_delay is None or math.isnan(float(base_delay)):
            base_delay = 1000
        else:
            base_delay = float(base_delay)
    except (TypeError, ValueError):
        base_delay = 1000
    base_delay = max(0.1, base_delay) # Ensure positive and avoid 0

    # Clean max_delay
    try:
        if max_delay is None or math.isnan(float(max_delay)):
            max_delay = 60000
        else:
            max_delay = float(max_delay)
    except (TypeError, ValueError):
        max_delay = 60000
    max_delay = max(base_delay, max_delay) # Ensure max_delay >= base_delay

    # Clean jitter_factor
    try:
        if jitter_factor is None or math.isnan(float(jitter_factor)):
            jitter_factor = 0.5
        else:
            jitter_factor = float(jitter_factor)
    except (TypeError, ValueError):
        jitter_factor = 0.5
    jitter_factor = max(0.0, min(1.0, jitter_factor)) # Clamp to [0, 1]

    # Calculate exponential backoff
    try:
        # 2 ** attempt can overflow if attempt is very large
        # limit attempt to reasonable number so that 2 ** attempt doesn't overflow float
        safe_attempt = min(attempt, 1000)
        exponential_delay = base_delay * (2 ** safe_attempt)
    except OverflowError:
        exponential_delay = float('inf')

    # Cap at max_delay
    delay = min(exponential_delay, max_delay)

    # Apply jitter
    if jitter_factor > 0:
        # Full Jitter approach: delay = random_between(delay * (1 - jitter_factor), delay)
        # or simple random variation.
        # Requirements state "jitter (randomization) using random.uniform(0, delay)" or similar.
        # Let's apply standard jitter: delay - random jitter
        jitter_amount = delay * jitter_factor
        delay = delay - random.uniform(0, jitter_amount)

    return delay
