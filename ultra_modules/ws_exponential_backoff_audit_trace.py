import math
import random
import time

class WSRetryStateMachine:
    def __init__(self, base_delay=1000, max_delay=60000, jitter_factor=0.5):
        self.state = {
            'attempt': 0,
            'base_delay': self._clean_number(base_delay, 1000, min_val=0.1),
            'max_delay': self._clean_number(max_delay, 60000, min_val=0.1),
            'jitter_factor': self._clean_number(jitter_factor, 0.5, min_val=0.0, max_val=1.0)
        }

        # Ensure max_delay >= base_delay
        if self.state['max_delay'] < self.state['base_delay']:
            self.state['max_delay'] = self.state['base_delay']

        self.audit_log = []

    def _clean_number(self, val, default_val, min_val=None, max_val=None):
        try:
            if val is None or math.isnan(float(val)):
                v = default_val
            else:
                v = float(val)
        except (TypeError, ValueError):
            v = default_val

        if min_val is not None:
            v = max(min_val, v)
        if max_val is not None:
            v = min(max_val, v)

        return v

    def calculate_next_delay(self):
        attempt = self.state['attempt']
        base_delay = self.state['base_delay']
        max_delay = self.state['max_delay']
        jitter_factor = self.state['jitter_factor']

        # Exponential backoff
        # Using 2 ** attempt, capped by max_delay to prevent huge numbers
        # If attempt is very large, math.pow could overflow, so we cap attempt
        # 2^30 * 1000 is way bigger than any reasonable max_delay
        safe_attempt = min(attempt, 30)

        exp_delay = base_delay * (2 ** safe_attempt)
        exp_delay = min(exp_delay, max_delay)

        # Jitter
        jitter_amount = exp_delay * jitter_factor
        jitter_val = random.uniform(-jitter_amount, jitter_amount)

        final_delay = max(0.1, exp_delay + jitter_val)

        return {
            'attempt': attempt,
            'exp_delay': exp_delay,
            'jitter_amount': jitter_amount,
            'jitter_val': jitter_val,
            'final_delay': final_delay
        }

    def process_reconnect_request(self, external_attempt=None):
        pre_state = self.state.copy()

        # Use provided attempt if valid, otherwise increment
        if external_attempt is not None:
            cleaned_attempt = int(min(self._clean_number(external_attempt, pre_state['attempt'] + 1, min_val=0), 10**9))
            self.state['attempt'] = cleaned_attempt
        else:
            self.state['attempt'] = pre_state['attempt'] + 1

        calc_result = self.calculate_next_delay()

        audit_entry = {
            'timestamp': time.time(),
            'pre_state': pre_state,
            'post_state': self.state.copy(),
            'calculation': calc_result,
            'diff': {
                'attempt_diff': self.state['attempt'] - pre_state['attempt']
            }
        }

        self.audit_log.append(audit_entry)

        # Frontend needs a clean result
        return {
            'delay_ms': calc_result['final_delay'],
            'attempt': self.state['attempt'],
            'audit_trace': audit_entry # Provided for backend logic
        }

    def reset(self):
        pre_state = self.state.copy()
        self.state['attempt'] = 0

        audit_entry = {
            'timestamp': time.time(),
            'action': 'reset',
            'pre_state': pre_state,
            'post_state': self.state.copy(),
            'diff': {
                'attempt_diff': self.state['attempt'] - pre_state['attempt']
            }
        }
        self.audit_log.append(audit_entry)

        return {
            'status': 'reset_successful',
            'attempt': 0
        }
