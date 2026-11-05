import time
from typing import Dict, Any, List, Tuple, Optional

def init_state(capacity: int = 100, refill_rate: float = 10.0) -> Dict[str, Any]:
    """
    Initialize the rate limiter and queue state.
    """
    # Handle missing or dirty data
    try:
        capacity = int(capacity)
        if capacity <= 0:
            capacity = 100
    except (ValueError, TypeError):
        capacity = 100

    try:
        refill_rate = float(refill_rate)
        if refill_rate <= 0:
            refill_rate = 10.0
    except (ValueError, TypeError):
        refill_rate = 10.0

    return {
        "capacity": capacity,
        "tokens": float(capacity),
        "refill_rate": refill_rate,
        "last_refill_time": time.time(),
        "queue": []
    }

def clean_request_data(request: Any) -> Dict[str, Any]:
    """
    Silently clean request data, ensuring it's a dictionary.
    """
    if isinstance(request, dict):
        return request
    elif request is None:
        return {}
    else:
        return {"data": str(request)}

def refill_tokens(state: Dict[str, Any], current_time: Optional[float] = None) -> Dict[str, Any]:
    """
    Refill tokens based on the time elapsed.
    """
    if not isinstance(state, dict):
        state = init_state()

    capacity = state.get("capacity", 100)
    tokens = state.get("tokens", capacity)
    refill_rate = state.get("refill_rate", 10.0)
    last_refill_time = state.get("last_refill_time", time.time())
    queue = state.get("queue", [])

    if current_time is None:
        current_time = time.time()

    # Handle dirty current_time (e.g. going backwards or invalid types)
    try:
        current_time = float(current_time)
    except (ValueError, TypeError):
        current_time = time.time()

    elapsed = current_time - last_refill_time
    if elapsed < 0:
        elapsed = 0.0 # time went backwards, ignore

    new_tokens = min(float(capacity), float(tokens) + elapsed * refill_rate)

    return {
        "capacity": capacity,
        "tokens": new_tokens,
        "refill_rate": refill_rate,
        "last_refill_time": current_time,
        "queue": queue
    }

def process_request(state: Dict[str, Any], request: Any = None, current_time: Optional[float] = None) -> Tuple[Dict[str, Any], bool]:
    """
    Process a request. If enough tokens, consume one and return True.
    Otherwise, enqueue the request and return False (HTTP 429).
    """
    cleaned_request = clean_request_data(request)
    state = refill_tokens(state, current_time)

    if state["tokens"] >= 1.0:
        state["tokens"] -= 1.0
        return state, True
    else:
        state = enqueue_request(state, cleaned_request)
        return state, False

def enqueue_request(state: Dict[str, Any], request: Any = None) -> Dict[str, Any]:
    """
    Enqueue a request for retry.
    """
    if not isinstance(state, dict):
        state = init_state()

    cleaned_request = clean_request_data(request)
    new_state = dict(state)
    if "queue" not in new_state or not isinstance(new_state["queue"], list):
        new_state["queue"] = []

    new_state["queue"] = new_state["queue"] + [cleaned_request]
    return new_state

def dequeue_requests(state: Dict[str, Any], max_items: int = 10) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Dequeue up to max_items requests.
    """
    if not isinstance(state, dict):
        state = init_state()

    try:
        max_items = int(max_items)
        if max_items <= 0:
            max_items = 10
    except (ValueError, TypeError):
        max_items = 10

    new_state = dict(state)
    if "queue" not in new_state or not isinstance(new_state["queue"], list):
        new_state["queue"] = []

    queue = new_state["queue"]
    dequeued = queue[:max_items]
    new_state["queue"] = queue[max_items:]

    return new_state, dequeued

def process_queue(state: Dict[str, Any], current_time: Optional[float] = None) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Try to process as many requests from the queue as possible.
    Returns the new state and the list of successfully processed requests.
    """
    state = refill_tokens(state, current_time)

    processed = []
    while state["tokens"] >= 1.0 and len(state.get("queue", [])) > 0:
        state["tokens"] -= 1.0
        # dequeue one
        queue = state["queue"]
        req = queue[0]
        state["queue"] = queue[1:]
        processed.append(req)

    return state, processed
