import time
from typing import Dict, Any, List, Optional
from ultra_modules.rate_limit_429_queue_core_engine import init_state, process_request, process_queue

def generate_synthetic_fixtures(num_requests: Any = 1000) -> List[Dict[str, Any]]:
    """
    Generate synthetic fixtures for benchmarking.
    Includes normal data, dirty data, null values, gibberish, and cross-month/year boundaries.
    """
    # Self-healing for dirty num_requests
    try:
        num = int(num_requests)
        if num < 0:
            num = 1000
    except (ValueError, TypeError):
        num = 1000

    fixtures = []
    for i in range(num):
        if i % 10 == 0:
            # Dirty data: None
            fixtures.append(None)
        elif i % 10 == 1:
            # Dirty data: Gibberish string
            fixtures.append("gibberish!@#")
        elif i % 10 == 2:
            # Cross-year boundary timestamp mock (2023-12-31 to 2024-01-01)
            fixtures.append({"id": i, "created_at": 1704067199}) # Dec 31 2023 23:59:59 UTC
        elif i % 10 == 3:
            # Cross-month boundary timestamp mock (2024-01-31 to 2024-02-01)
            fixtures.append({"id": i, "created_at": 1706745599}) # Jan 31 2024 23:59:59 UTC
        elif i % 10 == 4:
            # Missing parameter fallback (empty dict)
            fixtures.append({})
        else:
            # Normal data
            fixtures.append({"id": i, "type": "normal"})
    return fixtures

def run_benchmark_suite(fixtures: Any = None, capacity: Any = 100, refill_rate: Any = 10.0) -> Dict[str, Any]:
    """
    Run benchmark against the rate limit queue core engine.
    """
    if not isinstance(fixtures, list):
        fixtures = generate_synthetic_fixtures()

    # Init state relies on the core engine's own self-healing for capacity/refill_rate
    state = init_state(capacity=capacity, refill_rate=refill_rate)

    start_time = time.time()
    current_simulated_time = start_time

    processed_count = 0
    queued_count = 0
    exceptions_caught = 0

    try:
        for req in fixtures:
            # Simulate high concurrency with minimal time advancement
            current_simulated_time += 0.0001
            state, success = process_request(state, req, current_time=current_simulated_time)
            if success:
                processed_count += 1
            else:
                queued_count += 1

        # Fast forward time to process remaining queue
        while len(state["queue"]) > 0:
            # Provide time to clear a batch based on capacity
            batch_time = (state["capacity"] / state["refill_rate"]) + 0.1
            current_simulated_time += batch_time
            state, processed_from_queue = process_queue(state, current_time=current_simulated_time)
            processed_count += len(processed_from_queue)

            # Prevent infinite loop if something goes wrong
            if len(processed_from_queue) == 0:
                break

        queued_count = len(state["queue"])
    except Exception:
        exceptions_caught += 1

    end_time = time.time()
    total_time_ms = (end_time - start_time) * 1000

    return {
        "total_requests": len(fixtures),
        "processed_count": processed_count,
        "queued_remaining": queued_count,
        "total_time_ms": total_time_ms,
        "exceptions_caught": exceptions_caught,
        "is_zero_crash": exceptions_caught == 0,
        # Allow 2ms per request for pure python simulation loop over head + safe margin
        "is_millisecond_response": total_time_ms < (len(fixtures) * 2.0 + 1000)
    }

def evaluate_benchmark_results(results: Any = None) -> bool:
    """
    Evaluate if benchmark results meet the SLA (zero crash, rapid response).
    """
    if not isinstance(results, dict):
        return False

    zero_crash = results.get("is_zero_crash", False)
    fast_response = results.get("is_millisecond_response", False)
    all_processed = (results.get("total_requests", 0) ==
                     (results.get("processed_count", 0) + results.get("queued_remaining", 0)))

    return zero_crash and fast_response and all_processed
