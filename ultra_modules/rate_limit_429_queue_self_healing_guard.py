import time
import copy
from typing import Dict, Any, List, Tuple, Optional

def _refill_tokens(state: Dict[str, Any]) -> None:
    """Internal function to refill tokens based on time elapsed."""
    now = time.time()
    elapsed = now - state["last_refill_time"]
    tokens_to_add = elapsed * state["refill_rate"]
    state["tokens"] = min(state["capacity"], state["tokens"] + tokens_to_add)
    state["last_refill_time"] = now

def init_state(capacity: int = 100, refill_rate: float = 10.0) -> Dict[str, Any]:
    """
    Initialize the rate limiter, queue, and snapshot history.
    Includes silent self-healing for missing/abnormal parameters.
    """
    # Self-healing for capacity
    try:
        capacity = int(capacity)
        if capacity <= 0:
            capacity = 100
    except (ValueError, TypeError):
        capacity = 100

    # Self-healing for refill_rate
    try:
        refill_rate = float(refill_rate)
        if refill_rate <= 0.0:
            refill_rate = 10.0
    except (ValueError, TypeError):
        refill_rate = 10.0

    return {
        "capacity": capacity,
        "tokens": float(capacity),
        "refill_rate": refill_rate,
        "last_refill_time": time.time(),
        "queue": [],
        "history_snapshots": []
    }

def process_message(state: Dict[str, Any], message: Dict[str, Any], message_cost: int = 1) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Process a message through the token bucket rate limiter.
    Zero message loss: messages exceeding limits are queued.
    Includes snapshot mechanism for 5-second undo.
    """
    # Self-healing for message
    if not isinstance(message, dict):
        message = {"content": str(message)} if message is not None else {"content": ""}

    # Self-healing for message_cost
    try:
        message_cost = int(message_cost)
        if message_cost <= 0:
            message_cost = 1
    except (ValueError, TypeError):
        message_cost = 1

    now = time.time()

    # Clean history snapshots older than 5 seconds
    state["history_snapshots"] = [
        snap for snap in state["history_snapshots"]
        if now - snap[0] <= 5.0
    ]

    # Create a snapshot before modifying state for the undo mechanism
    state_copy = {
        "capacity": state["capacity"],
        "tokens": state["tokens"],
        "refill_rate": state["refill_rate"],
        "last_refill_time": state["last_refill_time"],
        "queue": copy.deepcopy(state["queue"])
    }

    # Store snapshot (timestamp, state_copy)
    state["history_snapshots"].append((now, state_copy))

    # Refill tokens before processing
    _refill_tokens(state)

    # Queue the current message (Zero message loss retry queue)
    state["queue"].append({
        "message": message,
        "cost": message_cost,
        "timestamp": now
    })

    result_message = None

    # Process the first item in queue if we have enough tokens
    if state["queue"]:
        next_item = state["queue"][0]
        if state["tokens"] >= next_item["cost"]:
            state["tokens"] -= next_item["cost"]
            result_message = state["queue"].pop(0)["message"]

    return state, result_message

def undo_last_message(state: Dict[str, Any], undo_window: float = 5.0) -> Tuple[Dict[str, Any], bool]:
    """
    One-tap Undo snapshot mechanism.
    Reverts the state to the snapshot before the last processed message,
    if it falls within the undo_window (default 5 seconds).
    """
    now = time.time()

    # Clean old snapshots first
    state["history_snapshots"] = [
        snap for snap in state["history_snapshots"]
        if now - snap[0] <= undo_window
    ]

    if not state["history_snapshots"]:
        return state, False

    # Get the last valid snapshot
    last_timestamp, last_state_copy = state["history_snapshots"].pop()

    # Revert state variables
    state["capacity"] = last_state_copy["capacity"]
    state["tokens"] = last_state_copy["tokens"]
    state["refill_rate"] = last_state_copy["refill_rate"]
    state["last_refill_time"] = last_state_copy["last_refill_time"]
    state["queue"] = last_state_copy["queue"]

    return state, True
