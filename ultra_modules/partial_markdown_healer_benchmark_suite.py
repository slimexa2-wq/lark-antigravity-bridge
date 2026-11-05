import time
import random
from typing import List, Dict, Any, Optional

from ultra_modules.partial_markdown_healer_core_engine import heal_content

class BenchmarkResult:
    def __init__(self, total_cases: int, success_cases: int, total_time_ms: float, avg_time_ms: float, max_time_ms: float):
        self.total_cases = total_cases
        self.success_cases = success_cases
        self.total_time_ms = total_time_ms
        self.avg_time_ms = avg_time_ms
        self.max_time_ms = max_time_ms

def generate_synthetic_fixtures(num_cases: int = 100) -> List[Dict[str, Any]]:
    fixtures = []

    # 保证包含一些基础类型，避免全随机导致缺少代表性
    base_cases = [
        {"content": None, "format": "auto"},
        {"content": 123, "format": "auto"},
        {"content": "```python\nprint('hello')", "format": "auto"},
        {"content": "**bold text", "format": "auto"},
        {"content": "| col1 | col2 |\n|---|---|\n| val1 | val2 ", "format": "auto"},
        {"content": '{"name": "test", "value": [1, 2, 3', "format": "json"},
        {"content": '[{"name": "test"', "format": "json"},
    ]

    for case in base_cases:
        if len(fixtures) < num_cases:
            fixtures.append(case)

    # 制造各种异常或半截断数据
    formats = ["auto", "json", "", None]
    garbage_chars = ["\x00", "\x1f", "\ufffd", "❤️", "你好", " "]

    while len(fixtures) < num_cases:
        case_type = random.randint(1, 5)
        if case_type == 1:
            # 制造脏数据/乱码
            length = random.randint(0, 1000)
            content = "".join(random.choice(garbage_chars) for _ in range(length))
            fixtures.append({"content": content, "format": random.choice(formats)})
        elif case_type == 2:
            # 制造极长的未闭合 JSON
            length = random.randint(10, 500)
            content = '{"key": "value", "arr": [' + ",".join(str(i) for i in range(length))
            fixtures.append({"content": content, "format": "json"})
        elif case_type == 3:
            # 制造极长的未闭合 Markdown 块
            length = random.randint(10, 500)
            content = "```javascript\n" + "\n".join("console.log('test');" for _ in range(length))
            fixtures.append({"content": content, "format": "auto"})
        elif case_type == 4:
            # 跨年跨月边界 (Cross-year cross-month boundaries)
            # 例如在 JSON 截断或表格中出现包含跨年/跨月时间戳或日期字符串的半截断数据
            dates = ["2023-12-31T23:59:59Z", "2024-01-01T00:00:01Z", "2024-02-29T12:00:00Z", "2024-03-01T00:00:00Z"]
            content = f'{{"event": "boundary_test", "timestamp": "{random.choice(dates)}", "data": ['
            fixtures.append({"content": content, "format": "json"})
        else:
            # 完全随机组合
            content = random.choice([None, "", 0, 3.14, "null", "undefined"])
            fixtures.append({"content": content, "format": random.choice(formats)})

    return fixtures

def run_single_case(content: Any, format_hint: str) -> Dict[str, Any]:
    start = time.perf_counter()
    try:
        res = heal_content(content, format_hint)
        success = True
        error = None
    except Exception as e:
        res = None
        success = False
        error = str(e)
    end = time.perf_counter()

    return {
        "success": success,
        "time_ms": (end - start) * 1000,
        "result": res,
        "error": error
    }

def run_benchmark(num_cases: int = 100, concurrency: int = 1) -> BenchmarkResult:
    fixtures = generate_synthetic_fixtures(num_cases)

    # 简单实现，支持并发的话可以使用线程池。这里先用顺序执行，若并发数>1使用 ThreadPoolExecutor
    if concurrency <= 1:
        results = []
        start_time = time.perf_counter()
        for f in fixtures:
            results.append(run_single_case(f["content"], f["format"]))
        end_time = time.perf_counter()
    else:
        from concurrent.futures import ThreadPoolExecutor
        start_time = time.perf_counter()
        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [executor.submit(run_single_case, f["content"], f["format"]) for f in fixtures]
            results = [future.result() for future in futures]
        end_time = time.perf_counter()

    total_time_ms = (end_time - start_time) * 1000
    success_cases = sum(1 for r in results if r["success"])
    times = [r["time_ms"] for r in results]

    avg_time_ms = sum(times) / len(times) if times else 0.0
    max_time_ms = max(times) if times else 0.0

    return BenchmarkResult(
        total_cases=len(fixtures),
        success_cases=success_cases,
        total_time_ms=total_time_ms,
        avg_time_ms=avg_time_ms,
        max_time_ms=max_time_ms
    )
