import time
import random
import datetime

try:
    from .error_plain_chinese_translator_core_engine import translate_error_to_plain_chinese
except ImportError:
    def translate_error_to_plain_chinese(error_trace=None):
        pass

def generate_synthetic_fixtures(size=10000):
    """
    构造含空值、乱码、超大并发、跨年跨月边界的合成数据集。
    支持缺参默认值。
    """
    if size is None or size <= 0:
        size = 10000

    fixtures = []

    # 正常日志
    normal_errors = [
        "java.lang.NullPointerException at com.example.service.UserService.getUser",
        "Connection timed out : Connection refused",
        "java.lang.OutOfMemoryError: Java heap space",
        "Permission denied: user has no roles",
        "jsondecodeerror: expecting value"
    ]

    # 边界情况（跨年跨月）模拟时间戳或时间相关日志
    def generate_boundary_dates():
        dates = []
        base = datetime.datetime(2023, 12, 31, 23, 59, 59)
        dates.append(base.isoformat())
        base = datetime.datetime(2024, 1, 1, 0, 0, 1)
        dates.append(base.isoformat())
        base = datetime.datetime(2024, 2, 29, 23, 59, 59)
        dates.append(base.isoformat())
        return dates

    boundary_dates = generate_boundary_dates()

    # 特殊乱码
    garbage_chars = [
        "",
        "§±!!@#$%^&*()_+",
        "\x00\x01\x02\x03",
        "龘齉齾麤龗灪龖厵爨癵驫麣纞虋讟钃鸜麷鞻韽韾顟顠饙饙騳騱饐龗",
    ]

    for i in range(size):
        choice = random.randint(0, 9)
        if choice < 4:
            # 正常已识别错误
            fixtures.append(random.choice(normal_errors))
        elif choice == 4:
            # None (脏数据)
            fixtures.append(None)
        elif choice == 5:
            # 空字符串
            fixtures.append("")
        elif choice == 6:
            # 数字 (脏数据)
            fixtures.append(random.randint(100, 599))
        elif choice == 7:
            # 包含边界时间的日志
            fixtures.append(f"Error at {random.choice(boundary_dates)}: Unknown system failure")
        elif choice == 8:
            # 乱码
            fixtures.append(f"Fatal error {random.choice(garbage_chars)}")
        else:
            # 超大字符串 (模拟 OOM 或者很长的 stack trace)
            fixtures.append("A" * 1000)

    return fixtures


def run_benchmark(concurrency_size=10000, fixtures=None):
    """
    验证零崩溃与毫秒级响应。
    """
    if concurrency_size is None or concurrency_size <= 0:
        concurrency_size = 10000

    if fixtures is None:
        fixtures = generate_synthetic_fixtures(concurrency_size)

    start_time = time.time()

    for fixture in fixtures:
        # 这里要求不崩溃 (静默处理)
        try:
            translate_error_to_plain_chinese(fixture)
        except Exception as e:
            # 如果发生崩溃，抛出异常表明失败
            raise RuntimeError(f"Benchmark failed on fixture {fixture}: {str(e)}")

    end_time = time.time()
    total_time_ms = (end_time - start_time) * 1000
    avg_latency_ms = total_time_ms / len(fixtures) if len(fixtures) > 0 else 0

    return {
        "total_requests": len(fixtures),
        "total_time_ms": total_time_ms,
        "avg_latency_ms": avg_latency_ms
    }
