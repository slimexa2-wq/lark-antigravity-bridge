import json
import csv
import io
import random
import time
from typing import Dict, Any, Optional, Callable, Union, List

class WsReconnectionStateMachine:
    def __init__(self, max_retries: int = 5, base_delay: float = 1.0, max_delay: float = 60.0, sleep_fn: Callable = time.sleep):
        self.state = "disconnected"
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.retries = 0
        self.sleep_fn = sleep_fn

    def connect(self, connect_func: Callable[[], bool]) -> bool:
        self.state = "connecting"
        self.retries = 0

        while self.retries <= self.max_retries:
            try:
                if connect_func():
                    self.state = "connected"
                    self.retries = 0
                    return True
            except Exception:
                pass

            if self.retries == self.max_retries:
                break

            self.state = "reconnecting"
            delay = min(self.max_delay, self.base_delay * (2 ** self.retries))
            # 随机抖动 Jitter (0 到 delay * 0.5 之间的随机数，增加随机性)
            jitter = random.uniform(0, delay * 0.5)
            self.sleep_fn(delay + jitter)
            self.retries += 1

        self.state = "disconnected"
        return False

    def on_disconnect(self, connect_func: Callable[[], bool]) -> bool:
        """静默自愈重连 (Silent self-healing)"""
        self.state = "disconnected"
        return self.connect(connect_func)

class DataAdapter:
    @staticmethod
    def parse(data: str, fallback_defaults: Optional[Dict[str, Any]] = None) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        JSON/Excel(CSV)双模无感直出适配器
        自动检测数据格式，脏数据自愈，缺参默认兜底
        """
        if fallback_defaults is None:
            fallback_defaults = {"default_key": "default_value"}

        if not data or not isinstance(data, str) or not data.strip():
            return fallback_defaults

        data = data.strip()

        # 尝试 JSON 解析
        if data.startswith('{') or data.startswith('['):
            try:
                parsed = json.loads(data)
                return DataAdapter._apply_fallback(parsed, fallback_defaults)
            except json.JSONDecodeError:
                pass

        # 尝试 CSV (模拟 Excel 导出内容) 解析
        try:
            reader = csv.DictReader(io.StringIO(data))
            result = list(reader)
            if result and all(isinstance(v, str) for v in result[0].values()):
                return DataAdapter._apply_fallback(result, fallback_defaults)
        except Exception:
            pass

        # 脏数据自愈：都失败则直接返回兜底
        return fallback_defaults

    @staticmethod
    def _apply_fallback(parsed: Any, defaults: Dict[str, Any]) -> Any:
        if isinstance(parsed, dict):
            for k, v in defaults.items():
                if k not in parsed or parsed[k] is None or str(parsed[k]).strip() == "":
                    parsed[k] = v
            return parsed
        elif isinstance(parsed, list):
            res = []
            for item in parsed:
                if isinstance(item, dict):
                    for k, v in defaults.items():
                        if k not in item or item[k] is None or str(item[k]).strip() == "":
                            item[k] = v
                    res.append(item)
                else:
                    res.append(item)
            return res
        return parsed

def run_cli_one_click(*args, **kwargs) -> Dict[str, Any]:
    """
    零参数一键CLI入口
    """
    # 无需记忆复杂参数的极简调用接口，默认参数即跑通全流程
    mock_connection_failures = kwargs.get("mock_connection_failures", 2)
    input_data = kwargs.get("input_data", '{"app_id": "", "app_secret": ""}')
    defaults = kwargs.get("defaults", {"app_id": "cli_default_id", "app_secret": "cli_default_secret"})

    # 记录重连过程用于验证
    logs = []

    def dummy_sleep(duration):
        logs.append(f"sleep_{duration:.2f}")

    sm = WsReconnectionStateMachine(max_retries=5, base_delay=1.0, sleep_fn=dummy_sleep)

    attempts = [0]
    def mock_connect():
        attempts[0] += 1
        if attempts[0] <= mock_connection_failures:
            raise ConnectionError("Mock network failure")
        return True

    # 1. 启动自愈重连
    success = sm.connect(mock_connect)

    # 2. 适配器解析
    parsed_data = DataAdapter.parse(input_data, fallback_defaults=defaults)

    return {
        "connected": success,
        "state": sm.state,
        "logs": logs,
        "retries": sm.retries,
        "data": parsed_data
    }

if __name__ == "__main__":
    result = run_cli_one_click()
    print(json.dumps(result, indent=2, ensure_ascii=False))
