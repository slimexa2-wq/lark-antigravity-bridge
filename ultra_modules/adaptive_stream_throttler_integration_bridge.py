import time
from typing import Dict, Any, Tuple, Optional

class AdaptiveStreamThrottlerBridge:
    """
    Feishu / Lark stream card adaptive throttler bridge.
    Dynamic window 150ms~500ms, monotonic sequence lock.
    Zero-config, self-healing, automatic schema forward compatibility.
    """

    @classmethod
    def process(
        cls,
        event: Optional[Any] = None,
        state: Optional[Any] = None,
        current_time_ms: Optional[int] = None
    ) -> Tuple[Dict[str, Any], bool, Optional[Dict[str, Any]]]:
        """
        Process incoming event.
        Returns:
            Tuple[state, should_emit, cleaned_event]
        """
        if current_time_ms is None:
            current_time_ms = int(time.time() * 1000)

        # 1. State self-healing
        if not isinstance(state, dict):
            state = {}

        last_emit_time = state.get('last_emit_time', 0)
        if not isinstance(last_emit_time, (int, float)) or last_emit_time < 0 or last_emit_time > current_time_ms:
            last_emit_time = 0

        last_seq = state.get('last_seq', -1)
        if not isinstance(last_seq, int):
            try:
                last_seq = int(last_seq)
            except (ValueError, TypeError):
                last_seq = -1

        window_size = state.get('window_size', 150)
        if not isinstance(window_size, (int, float)) or window_size < 150 or window_size > 500:
            window_size = 150

        new_state = {
            'last_emit_time': last_emit_time,
            'last_seq': last_seq,
            'window_size': window_size
        }

        # 2. Event self-healing & schema auto-mapping
        if not isinstance(event, dict):
            return new_state, False, None

        cleaned_event = cls._auto_map_schema(event)

        # Extract sequence
        seq = cleaned_event.get('seq')
        if seq is None:
            seq = cleaned_event.get('sequence_id') # fallback

        if not isinstance(seq, int):
            try:
                seq = int(seq)
            except (ValueError, TypeError):
                return new_state, False, None

        cleaned_event['seq'] = seq

        # 3. Monotonic Sequence Lock
        if seq <= last_seq:
            # Out of order or duplicate
            return new_state, False, None

        # 4. Adaptive Throttling
        time_since_last = current_time_ms - last_emit_time
        should_emit = False

        if last_emit_time == 0 or time_since_last >= window_size:
            should_emit = True
            new_state['last_emit_time'] = current_time_ms

            # Adjust window
            if last_emit_time != 0:
                if time_since_last < window_size * 1.5:
                    new_state['window_size'] = min(500, window_size + 50)
                else:
                    new_state['window_size'] = max(150, window_size - 50)
        else:
            should_emit = False

        new_state['last_seq'] = seq

        return new_state, should_emit, cleaned_event

    @staticmethod
    def _auto_map_schema(event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically convert legacy fields to new schemas without manual tables.
        Uses rule-based heuristics to recognize old and new version field differences
        and silently map and convert them.
        """
        converted = {}
        for k, v in event.items():
            new_key = str(k)
            # Rule 1: msg -> message
            if 'msg' in new_key and 'message' not in new_key:
                new_key = new_key.replace('msg', 'message')
            # Rule 2: text -> content
            if new_key == 'text':
                new_key = 'content'
            # Rule 3: seq_id -> seq
            if new_key == 'seq_id':
                new_key = 'seq'
            converted[new_key] = v
        return converted
