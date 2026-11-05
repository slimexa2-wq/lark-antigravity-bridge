import time
import concurrent.futures
from typing import Callable, Any, List, Dict, Optional
import random

def generate_synthetic_fixtures(count: Optional[Any] = 100) -> List[Any]:
    """
    Generate synthetic dataset for approval callbacks.
    Includes normal, empty, garbage string, None, and cross-year/month boundary cases.
    Features strict zero-configuration fault tolerance.
    """
    # Self-healing: invalid or negative count defaults to 100
    if not isinstance(count, int) or count <= 0:
        count = 100

    fixtures = []

    # Predefined extreme boundary cases
    boundary_cases = [
        None,
        {},
        {"action": {"value": {"action_type": "approve", "approval_id": "AP-20231231-9999"}}}, # cross year 2023->2024
        {"action": {"value": {"action_type": "reject", "approval_id": "AP-20240101-0001"}}}, # cross year 2023->2024
        {"action": {"value": {"action_type": "approve", "approval_id": "AP-20240229-0001"}}}, # leap year cross month
        {"action": {"value": {"action_type": "reject", "approval_id": "AP-20240301-0001"}}}, # leap year cross month
        {"action": {"value": {"action_type": "unknown_action", "approval_id": "123"}}},
        "invalid \x00\xff json string \n\r garbled", # garbled string
        '{"action": {"value": {"action_type": "approve", "approval_id": "456"}}}',
        [],
        12345,
        {"action": "not a dict"},
        {"action": {"value": "not a dict"}},
        {"action": {"value": {"action_type": "", "approval_id": None}}},
        {"action": {"value": {"action_type": None, "approval_id": "AP-123"}}},
        # deeply nested garbled data
        {"action": {"value": {"action_type": "approve", "extra": {"nested": "value"*1000}}}},
    ]

    for _ in range(count):
        # 30% boundary cases, 70% normal cases
        if random.random() < 0.3:
            fixtures.append(random.choice(boundary_cases))
        else:
            action_type = random.choice(["approve", "reject"])
            approval_id = f"AP-{random.randint(1000, 9999)}"
            fixtures.append({
                "action": {
                    "value": {
                        "action_type": action_type,
                        "approval_id": approval_id
                    }
                }
            })

    return fixtures

def run_benchmark(target_func: Optional[Callable] = None, fixtures: Optional[List[Any]] = None, concurrency_count: Optional[Any] = 10) -> Dict[str, Any]:
    """
    Run benchmark against target function with given fixtures.
    Validates zero-crash requirement and measures response time.
    """
    # Self-healing for missing parameters
    if target_func is None:
        # Provide a dummy fallback function if none provided
        target_func = lambda x: {}

    if not isinstance(fixtures, list):
        fixtures = generate_synthetic_fixtures(100)

    if not isinstance(concurrency_count, int) or concurrency_count <= 0:
        concurrency_count = 10

    if not fixtures:
        return {
            "success": True,
            "total_requests": 0,
            "success_count": 0,
            "error_count": 0,
            "average_latency_ms": 0.0,
            "max_latency_ms": 0.0,
            "zero_crash": True,
            "total_time_ms": 0.0
        }

    results = []
    errors = 0

    start_total_time = time.time()

    def worker(fixture: Any) -> float:
        start_time = time.time()
        try:
            target_func(fixture)
        except Exception:
            return -1.0 # Indicator of failure
        end_time = time.time()
        return (end_time - start_time) * 1000.0 # to milliseconds

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency_count) as executor:
        future_to_fixture = {executor.submit(worker, f): f for f in fixtures}
        for future in concurrent.futures.as_completed(future_to_fixture):
            latency = future.result()
            if latency < 0:
                errors += 1
            else:
                results.append(latency)

    end_total_time = time.time()

    success_count = len(results)
    avg_latency = sum(results) / success_count if success_count > 0 else 0.0
    max_latency = max(results) if success_count > 0 else 0.0

    return {
        "success": errors == 0,
        "total_requests": len(fixtures),
        "success_count": success_count,
        "error_count": errors,
        "average_latency_ms": avg_latency,
        "max_latency_ms": max_latency,
        "zero_crash": errors == 0,
        "total_time_ms": (end_total_time - start_total_time) * 1000.0
    }
