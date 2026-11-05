1. **Fix `flush()` and `isFinal` on 429 deadlock**:
    - In `flush()` or `push({ isFinal: true })`, if `isSending` is true, we should *not* aggressively call `clearTimeout(this.timer)` and try to reschedule if we are actually in a backoff state.
    - Instead of using `this.isSending = true` to represent the backoff wait, we should decouple "actively communicating with the network" from "waiting for backoff timer". We can introduce a `isBackingOff` state or check if the timer exists.
    - Alternatively, in `processNext()`, if it bails out due to `this.isSending`, it should not blindly clear the timer if one exists, but `scheduleSend` clears it before setting a new one.
    - Let's rethink the state: We need to know if a request is actively in-flight (`isInFlight`). We need to know if we are waiting for a backoff or coalesce window (`timer`). If `flush()` or `isFinal` is called, we should schedule a send *only if* we are not in-flight and not in a backoff. Actually, if we are in a backoff, we *must* wait for the backoff to finish. We cannot just bypass it with a 0ms delay. So `scheduleSend` shouldn't override a backoff timer.
2. **Fix delayed flush resolution**: If a flush is pending, when the in-flight request finishes, it should send the next frame immediately instead of waiting for `coalesceWindowMs`.
3. **Verify changes in `src/card/adaptive-throttler.ts`** using `read_file`.
4. **Edit `tests/unit/card/adaptive-throttler.test.ts`** to add a test case calling `flush()` during a 429 backoff period.
5. **Verify changes in test file** using `read_file`.
6. **Run the tests** using `pnpm vitest run tests/unit/card/adaptive-throttler.test.ts` to ensure the changes are correct.
7. **Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.**
8. **Submit PR**.
