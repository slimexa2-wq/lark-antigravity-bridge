import json
import logging
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)


class ApprovalOneTapCallbackIntegrationBridge:
    """
    High-risk outbound action Feishu card 'One-tap approve / One-tap reject' callback synchronizer.
    Provides seamless cross-system data contract bridging and schema automatic forward compatibility conversion.
    """

    def __init__(self):
        pass

    def sync_status(self, payload: Union[str, Dict[str, Any], Any] = None) -> Dict[str, Any]:
        """
        Process the callback payload automatically handling different schema versions,
        dirty data, and missing parameters.
        """
        # Default fallback
        if payload is None:
            return self._default_result()

        # Self-healing: if payload is a string, try to parse it
        parsed_data = {}
        if isinstance(payload, str):
            try:
                parsed_data = json.loads(payload)
            except json.JSONDecodeError:
                # Dirty data self-healing: return default but maybe extract raw string
                logger.warning("Invalid JSON payload received, falling back to default")
                return self._default_result(raw_payload=payload)
        elif isinstance(payload, dict):
            parsed_data = payload
        else:
            # Dirty data: unknown type
            return self._default_result(raw_payload=payload)

        return self._normalize_schema(parsed_data)

    def _normalize_schema(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically identify old and new version schema differences and silently map them.
        No manual configuration needed.
        """
        result = self._default_result()

        # 1. Action/Status
        # Old schema: 'action_name': 'approve' / 'reject'
        # New schema: 'action': {'value': 'APPROVE'}
        if 'action_name' in data:
            val = str(data['action_name']).upper()
            result['status'] = 'APPROVED' if val in ('APPROVE', 'APPROVED') else ('REJECTED' if val in ('REJECT', 'REJECTED') else 'UNKNOWN')
        elif 'action' in data and isinstance(data['action'], dict) and 'value' in data['action']:
            val = str(data['action']['value']).upper()
            result['status'] = 'APPROVED' if val in ('APPROVE', 'APPROVED') else ('REJECTED' if val in ('REJECT', 'REJECTED') else 'UNKNOWN')
        elif 'status' in data:
            val = str(data['status']).upper()
            result['status'] = 'APPROVED' if val in ('APPROVE', 'APPROVED') else ('REJECTED' if val in ('REJECT', 'REJECTED') else 'UNKNOWN')

        # 2. User ID
        # Old schema: 'open_id': 'ou_12345'
        # New schema: 'user': {'id': 'ou_12345'}
        if 'open_id' in data:
            result['user_id'] = str(data['open_id'])
        elif 'user' in data and isinstance(data['user'], dict) and 'id' in data['user']:
            result['user_id'] = str(data['user']['id'])
        elif 'user_id' in data:
            result['user_id'] = str(data['user_id'])

        # 3. Instance/Task ID
        # Old schema: 'instance_code': 'xxx'
        # New schema: 'task': {'id': 'xxx'}
        if 'instance_code' in data:
            result['task_id'] = str(data['instance_code'])
        elif 'task' in data and isinstance(data['task'], dict) and 'id' in data['task']:
            result['task_id'] = str(data['task']['id'])
        elif 'task_id' in data:
            result['task_id'] = str(data['task_id'])

        return result

    def _default_result(self, raw_payload: Any = None) -> Dict[str, Any]:
        return {
            'status': 'UNKNOWN',
            'user_id': 'UNKNOWN_USER',
            'task_id': 'UNKNOWN_TASK',
            'raw_payload': raw_payload if raw_payload is not None else {}
        }
