import unittest
from ultra_modules.slash_command_quick_menu_cli_one_click import QuickCommandRouter, cli_entry_point

class TestQuickCommandRouter(unittest.TestCase):
    def setUp(self):
        self.router = QuickCommandRouter()

    def test_normal_json_output(self):
        res = self.router.execute("/周报", {"content": "This week I worked on ABC"}, "json")
        self.assertEqual(res["format"], "json")
        self.assertEqual(res["data"]["title"], "Weekly Report")
        self.assertEqual(res["data"]["content"], "This week I worked on ABC")
        self.assertTrue(isinstance(res["output"], str))

    def test_missing_params_fallback(self):
        res = cli_entry_point()
        self.assertEqual(res["format"], "json")
        self.assertEqual(res["data"]["title"], "System Status")

        res2 = self.router.execute(" /未知 ", None, "unknown")
        self.assertEqual(res2["format"], "json")
        self.assertEqual(res2["data"]["title"], "System Status")

    def test_dirty_data_self_healing(self):
        res = self.router.execute("/提成", ["dirty", "list"], "excel")
        self.assertEqual(res["format"], "excel")
        self.assertEqual(res["data"]["amount"], 0.0)

        res2 = self.router.execute("/提成", {"": "value", None: "value2", "amount": "100.5"}, "csv")
        self.assertEqual(res2["data"]["amount"], 100.5)
        self.assertEqual(res2["data"]["calculated"], 10.05)

        res_invalid_amount = self.router.execute("/提成", {"amount": {}})
        self.assertEqual(res_invalid_amount["data"]["amount"], 0.0)

        res3 = self.router.execute("/标书", '{"project": "Project X"}', "json")
        self.assertEqual(res3["data"]["project"], "Project X")

        res4 = self.router.execute("/漫剧", "invalid json string", "json")
        self.assertEqual(res4["data"]["name"], "Unknown Drama")

    def test_extreme_boundaries(self):
        res = self.router.execute(command=123, args=object(), output_format=999)
        self.assertEqual(res["format"], "json")
        self.assertEqual(res["data"]["title"], "System Status")

        res_clean = self.router.execute("/状态", args={"  valid_key  ": 123})
        self.assertEqual(res_clean["status"], "success")

    def test_excel_csv_output(self):
        res = self.router.execute("/标书", {"project": "Proj", "price": 500}, "excel")
        self.assertEqual(res["format"], "excel")
        self.assertTrue("title,project,price" in res["output"])
        self.assertTrue("Bid Document,Proj,500" in res["output"])

    def test_all_commands(self):
        for cmd in ["/周报", "/提成", "/漫剧", "/标书", "/状态"]:
            res = self.router.execute(cmd, {}, "json")
            self.assertEqual(res["status"], "success")

if __name__ == "__main__":  # pragma: no cover
    unittest.main()
