1. **src/card/run-renderer.ts**: Optimize debounce strategy for high-frequency streaming message updates & Exception Reconnect (异常重连).
   - Add `update_multi: true` to the config object in `renderCard()` directly, similar to how it is in `renderRichCard()`.
   - Add a `reconnectButton(options)` helper method. If `state.terminal === 'error'`, add this reconnect button to `elements` in both `renderCard()` and `renderRichCard()`.
   - The button should have `cmd: 'reconnect'`.

2. **src/card/dispatcher.ts**: Add debouncing to card action clicks.
   - We need to prevent rapid, repetitive button clicks from triggering multiple identical actions in quick succession.
   - We can achieve this by adding a memory map of recent actions per `operatorId + chatId + cmd` within a short time window (e.g., 2-3 seconds) and dropping duplicates. Or we can just drop rapid duplicate commands from the same user.
   - When a user clicks a button with an agent callback (e.g. `__bridge_cb = true`), if the run no longer exists (e.g. `verifyBridgeToken` fails due to missing run), gracefully fall back or notify the user. Currently it silently returns `false`. We can modify `verifyBridgeToken` to return an enum or string reason, and if it's missing token/run, perhaps we do not process the click, but we don't need a `/reconnect` synthesized. Actually, looking at the instruction, "优化... 异常重连", this likely refers only to adding the reconnect button to the card renderer. I will implement a basic debounce map for card dispatcher commands.

3. **src/agent/antigravity/json.ts**: Fix stability for parsing super-large JSON streams.
   - In `translateAntigravityStreamLine`, `step.tool_info?.output` might be an object instead of a string in some large JSON outputs. Modify the assignment:
     ```ts
     const output =
       typeof step.tool_info?.output === 'string'
         ? step.tool_info.output
         : typeof step.tool_info?.output === 'object' && step.tool_info.output !== null
           ? (() => { try { return JSON.stringify(step.tool_info.output) } catch { return '' } })()
           : typeof errMsg === 'string'
             ? errMsg
             : '';
     ```

4. **Tests**: Add Vitest unit tests for the modified files.
   - Create `src/agent/antigravity/__tests__/json.test.ts` to test `translateAntigravityStreamLine` with object output.
   - Create `src/card/__tests__/run-renderer.test.ts` to test the `update_multi` flag and reconnect button rendering.
   - Create `src/card/__tests__/dispatcher.test.ts` to test debounced card clicks.
   - Run `npx vitest run` to execute all unit tests and verify the changes.

5. **Pre-commit**.
   - Complete pre-commit steps to ensure proper testing, verifications, reviews and reflections are done.

6. **Submit**.
   - Submit the PR.
