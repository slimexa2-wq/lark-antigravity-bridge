"""
Adaptive Stream Throttler Core Engine

This module implements an adaptive stream throttler with a dynamic window
(150ms ~ 500ms) and monotonic sequence locking for processing events.
It features zero-configuration fault tolerance and automatic bad data cleaning.
"""

from typing import Dict, Any, Tuple, Optional
import time

def process_stream_event(
    state: Optional[Dict[str, Any]],
    event: Optional[Dict[str, Any]],
    current_time_ms: Optional[int] = None
) -> Tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]:
    """
    Process an incoming stream event and determine if it should be emitted.

    Args:
        state: The current state of the throttler (will provide a default if None or invalid).
        event: The incoming event containing at least a 'seq' (sequence number).
        current_time_ms: Current time in milliseconds. Defaults to current system time.

    Returns:
        Tuple containing:
        - The new updated state.
        - Boolean indicating whether the event should be emitted.
        - The cleaned event data (or None if discarded).
    """
    if current_time_ms is None:
        current_time_ms = int(time.time() * 1000)

    # 1. Dirty data silent cleaning and default initialization for state
    if not isinstance(state, dict):
        state = {}

    last_emit_time = state.get('last_emit_time', 0)
    if not isinstance(last_emit_time, (int, float)) or last_emit_time < 0 or last_emit_time > current_time_ms:
        last_emit_time = 0

    last_seq = state.get('last_seq', -1)
    if not isinstance(last_seq, int):
        last_seq = -1

    window_size = state.get('window_size', 150)
    if not isinstance(window_size, (int, float)) or window_size < 150 or window_size > 500:
        window_size = 150

    # 2. Event validation and cleaning
    if not isinstance(event, dict):
        # Invalid event, discard silently
        return {'last_emit_time': last_emit_time, 'last_seq': last_seq, 'window_size': window_size}, False, None

    # Extract sequence number, default to -1 if invalid
    seq = event.get('seq')
    if not isinstance(seq, int):
        # We try to parse it if it's a string representation of int
        try:
            seq = int(seq)
        except (TypeError, ValueError):
            # Invalid seq, discard silently
            return {'last_emit_time': last_emit_time, 'last_seq': last_seq, 'window_size': window_size}, False, None

    # 3. Monotonic sequence locking
    if seq <= last_seq:
        # Out of order or duplicate event, discard
        return {'last_emit_time': last_emit_time, 'last_seq': last_seq, 'window_size': window_size}, False, None

    # 4. Adaptive throttling logic
    time_since_last_emit = current_time_ms - last_emit_time

    if last_emit_time == 0 or time_since_last_emit >= window_size:
        # Allow emit
        should_emit = True
        new_last_emit_time = current_time_ms

        # Adjust window size adaptively
        # If we emit, and we waited a long time, we can shrink the window towards 150ms
        # If we emit frequently, the window might need to be increased if there's high pressure (simulated here)
        # We use a simple adaptive rule based on event frequency.
        # Since we don't have event pressure explicit, let's just implement a simple logic:
        # If it comes very fast (time_since_last_emit is close to window_size), we might increase window size slightly to reduce load.
        # If it comes slowly (time_since_last_emit >> window_size), we shrink window size towards 150ms.

        if last_emit_time != 0:
            if time_since_last_emit < window_size * 1.5:
                # High frequency, increase window size, max 500
                new_window_size = min(500, window_size + 50)
            else:
                # Low frequency, decrease window size, min 150
                new_window_size = max(150, window_size - 50)
        else:
            new_window_size = window_size
    else:
        # Throttle
        should_emit = False
        new_last_emit_time = last_emit_time
        new_window_size = window_size

    # We only update last_seq if we process the event. But wait, if we throttle, do we discard the event?
    # Usually, a throttler might hold the event or discard it. The prompt says "adaptive stream throttler... monotonic sequence lock".
    # For a stream like UI updates, if it's throttled, we usually skip updating until the window opens, but we should always update the sequence so we don't process older ones.
    # However, if we discard it, the next event will have a higher sequence.
    # If the user expects the latest state, we should probably update `last_seq` even if throttled, OR we only update `last_seq` when emitted.
    # Actually, for stream events, if we throttle, it means we ignore this event and wait for a newer one.
    # So we update `last_seq` to the current `seq` regardless of emission, so we drop any older events.
    # Let's update `last_seq` to `seq`.

    new_state = {
        'last_emit_time': new_last_emit_time,
        'last_seq': seq,
        'window_size': new_window_size
    }

    # Ensure event is a clean dict with just seq if there's garbage? No, keep the dict but ensure seq is an int.
    cleaned_event = dict(event)
    cleaned_event['seq'] = seq

    return new_state, should_emit, cleaned_event
