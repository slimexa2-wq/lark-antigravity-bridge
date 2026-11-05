import unittest
from ultra_modules.mobile_table_digest_formatter_core_engine import format_mobile_table_digest

class TestMobileTableDigestFormatterCoreEngine(unittest.TestCase):

    def test_normal_table_data(self):
        # Normal data with 4 columns and 4 rows (should take up to 3 columns and 3 rows defaults)
        data = [
            {"Name": "Alice", "Age": 25, "Status": "OK", "ID": 1},
            {"Name": "Bob", "Age": 30, "Status": "Error", "ID": 2},
            {"Name": "Charlie", "Age": 35, "Status": "OK", "ID": 3},
            {"Name": "David", "Age": 40, "Status": "OK", "ID": 4}
        ]

        card = format_mobile_table_digest(
            table_data=data,
            summary_columns=["Name", "Status"],
            title="User Status",
            attachment_url="https://example.com/download"
        )

        self.assertEqual(card["msg_type"], "interactive")
        self.assertEqual(card["card"]["header"]["title"]["content"], "User Status")
        elements = card["card"]["elements"]

        # 3 rows of data + hr + action (attachment) -> 5 elements
        self.assertEqual(len(elements), 5)

        # Verify first row
        self.assertEqual(elements[0]["tag"], "markdown")
        self.assertEqual(elements[0]["content"], "Name: Alice | Status: OK")

        # Verify attachment action button
        self.assertEqual(elements[4]["tag"], "action")
        self.assertEqual(elements[4]["actions"][0]["url"], "https://example.com/download")

    def test_dirty_data_self_healing(self):
        # Invalid JSON string for table_data, summary_columns not a list, etc.
        card = format_mobile_table_digest(
            table_data="this is not a valid json",
            summary_columns="Name", # Should cast to ["Name"]
            title=123 # Should cast to "123"
        )

        self.assertEqual(card["card"]["header"]["title"]["content"], "123")

        elements = card["card"]["elements"]
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["content"], "暂无摘要数据")

        # Test table_data string which is valid json but not list
        card2 = format_mobile_table_digest(table_data='{"a": 1}')
        self.assertEqual(card2["card"]["elements"][0]["content"], "暂无摘要数据")

        # Test table_data is valid json list of string (not dict)
        card3 = format_mobile_table_digest(table_data='["str", "str2"]')
        self.assertEqual(card3["card"]["elements"][0]["content"], "暂无摘要数据")

        # Test invalid table_data types
        card4 = format_mobile_table_digest(table_data=12345)
        self.assertEqual(card4["card"]["elements"][0]["content"], "暂无摘要数据")

    def test_missing_parameter_default_fallbacks(self):
        # Completely empty parameters
        card = format_mobile_table_digest()

        self.assertEqual(card["card"]["header"]["title"]["content"], "数据摘要")
        elements = card["card"]["elements"]

        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0]["content"], "暂无摘要数据")

    def test_extreme_boundary_conditions(self):
        # Empty list of dicts, no columns given
        data = [
            {"Col1": 1, "Col2": 2, "Col3": 3, "Col4": 4}
        ]

        # summary_columns will automatically use up to 3 keys of the first row
        card = format_mobile_table_digest(table_data=data)
        elements = card["card"]["elements"]
        self.assertEqual(len(elements), 1)
        # Assuming dict order is preserved (python 3.7+), it should extract first 3 keys
        self.assertEqual(elements[0]["content"], "Col1: 1 | Col2: 2 | Col3: 3")

        # table_data containing both dicts and non-dicts, summary_columns containing unexisting columns
        data2 = [
            123,
            {"ColA": "A"},
            "test",
            {}
        ]
        card2 = format_mobile_table_digest(table_data=data2, summary_columns=["ColA", "ColB"])
        elements2 = card2["card"]["elements"]
        self.assertEqual(len(elements2), 2)
        # First dict (index 1)
        self.assertEqual(elements2[0]["content"], "ColA: A | ColB: -")
        # Second dict (index 3)
        self.assertEqual(elements2[1]["content"], "ColA: - | ColB: -")

    def test_anomaly_highlighting(self):
        data = [
            {"Name": "Alice", "Status": "Success"},
            {"Name": "Bob", "Status": "Failed"},
            {"Name": "Charlie", "Status": "Pending"}
        ]

        def anomaly_func(val):
            if not isinstance(val, str): return False
            return val == "Failed"

        def crash_anomaly_func(val):
            raise Exception("Boom!")

        anomaly_rules = {
            "Status": anomaly_func,
            "Name": ["Bob", "Eve"] # Test list
        }

        card = format_mobile_table_digest(
            table_data=data,
            summary_columns=["Name", "Status"],
            anomaly_rules=anomaly_rules
        )

        elements = card["card"]["elements"]
        self.assertEqual(len(elements), 3)

        # Alice is normal
        self.assertEqual(elements[0]["content"], "Name: Alice | Status: Success")
        # Bob is failed and name is Bob (both anomalies)
        self.assertEqual(elements[1]["content"], "Name: <font color='red'>Bob</font> | Status: <font color='red'>Failed</font>")

        # Test rule causing crash and scalar rule
        anomaly_rules2 = {
            "Status": crash_anomaly_func,
            "Name": "Charlie"
        }
        card2 = format_mobile_table_digest(
            table_data=data,
            summary_columns=["Name", "Status"],
            anomaly_rules=anomaly_rules2
        )
        elements2 = card2["card"]["elements"]
        self.assertEqual(elements2[1]["content"], "Name: Bob | Status: Failed") # function crashes -> normal
        self.assertEqual(elements2[2]["content"], "Name: <font color='red'>Charlie</font> | Status: Pending") # scalar matching

if __name__ == '__main__':
    unittest.main()
