import unittest
from ultra_modules.ws_exponential_backoff_cli_one_click import WsReconnectionStateMachine, DataAdapter, run_cli_one_click

class TestWsExponentialBackoffCliOneClick(unittest.TestCase):
    def test_normal_reconnection_and_jitter(self):
        logs = []
        def sleep_spy(duration):
            logs.append(duration)

        sm = WsReconnectionStateMachine(max_retries=3, base_delay=1.0, sleep_fn=sleep_spy)
        attempts = [0]
        def connect_func():
            attempts[0] += 1
            if attempts[0] < 3:
                raise Exception("Network error")
            return True

        res = sm.connect(connect_func)
        self.assertTrue(res)
        self.assertEqual(sm.state, "connected")
        self.assertEqual(len(logs), 2)
        # Check jitter inclusion: delay should be base * 2^retry + jitter
        # retry 0: base 1.0, jitter 0~0.5 -> 1.0~1.5
        self.assertTrue(1.0 <= logs[0] <= 1.5)
        # retry 1: base 2.0, jitter 0~1.0 -> 2.0~3.0
        self.assertTrue(2.0 <= logs[1] <= 3.0)

    def test_dirty_data_self_healing(self):
        # 脏数据自愈：无法解析的文本或非法类型，应该直接返回 default
        defaults = {"healed": True}
        self.assertEqual(DataAdapter.parse("just some random text not json or csv", fallback_defaults=defaults), defaults)
        self.assertEqual(DataAdapter.parse("   ", fallback_defaults=defaults), defaults)
        self.assertEqual(DataAdapter.parse(None, fallback_defaults=defaults), defaults)
        self.assertEqual(DataAdapter.parse("{invalid json", fallback_defaults=defaults), defaults)

    def test_missing_param_default_fallback(self):
        defaults = {"role": "user", "token": "default_token"}
        # JSON 缺失参数
        res_json = DataAdapter.parse('{"role": "admin"}', fallback_defaults=defaults)
        self.assertEqual(res_json["role"], "admin")
        self.assertEqual(res_json["token"], "default_token")

        # JSON 空值覆盖
        res_empty = DataAdapter.parse('{"role": "", "token": null}', fallback_defaults=defaults)
        self.assertEqual(res_empty["role"], "user")
        self.assertEqual(res_empty["token"], "default_token")

    def test_extreme_boundaries(self):
        # 重连失败超过最大次数
        logs = []
        sm = WsReconnectionStateMachine(max_retries=2, base_delay=1.0, sleep_fn=lambda x: logs.append(x))
        def connect_always_fail():
            raise Exception("Fail forever")

        res = sm.connect(connect_always_fail)
        self.assertFalse(res)
        self.assertEqual(sm.state, "disconnected")
        self.assertEqual(len(logs), 2) # retries: 0, 1 (since max_retries is 2, it breaks before sleeping on retry 2)

        # CLI 零参数调用兜底测试
        cli_res = run_cli_one_click()
        self.assertTrue(cli_res["connected"])
        self.assertEqual(cli_res["data"]["app_id"], "cli_default_id")

    def test_csv_excel_mode(self):
        defaults = {"status": "active", "score": "0"}
        csv_data = "name,status,score\nAlice,,90\nBob,inactive,\n"
        res = DataAdapter.parse(csv_data, fallback_defaults=defaults)

        self.assertTrue(isinstance(res, list))
        self.assertEqual(len(res), 2)

        # Alice 状态缺省 -> active
        self.assertEqual(res[0]["name"], "Alice")
        self.assertEqual(res[0]["status"], "active")
        self.assertEqual(res[0]["score"], "90")

        # Bob 分数缺省 -> 0
        self.assertEqual(res[1]["name"], "Bob")
        self.assertEqual(res[1]["status"], "inactive")
        self.assertEqual(res[1]["score"], "0")

if __name__ == '__main__':
    unittest.main()
