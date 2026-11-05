import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SequenceLock, AdaptiveStreamThrottler } from '../../../src/card/adaptive-throttler';

describe('SequenceLock', () => {
  it('acquires lock strictly monotonically', () => {
    const lock = new SequenceLock();
    expect(lock.current()).toBe(0);

    expect(lock.acquire(1)).toBe(true);
    expect(lock.current()).toBe(1);

    expect(lock.acquire(1)).toBe(false);
    expect(lock.current()).toBe(1);

    expect(lock.acquire(0)).toBe(false);
    expect(lock.current()).toBe(1);

    expect(lock.acquire(2)).toBe(true);
    expect(lock.current()).toBe(2);
  });

  it('getNext returns current + 1', () => {
    const lock = new SequenceLock();
    expect(lock.getNext()).toBe(1);
    lock.acquire(1);
    expect(lock.getNext()).toBe(2);
  });


describe('AdaptiveStreamThrottler', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('sends first packet with fast delay', async () => {
    const sendFn = vi.fn().mockResolvedValue(undefined);
    const throttler = new AdaptiveStreamThrottler(sendFn, { firstPacketDelayMs: 50 });

    throttler.push('hello');

    expect(sendFn).not.toHaveBeenCalled();

    // Fast path: < 50ms shouldn't send yet
    await vi.advanceTimersByTimeAsync(40);
    expect(sendFn).not.toHaveBeenCalled();

    // 50ms should trigger send
    await vi.advanceTimersByTimeAsync(10);

    expect(sendFn).toHaveBeenCalledTimes(1);
    expect(sendFn).toHaveBeenCalledWith('hello', 1);
  });

  it('debounces multiple fast packets', async () => {
    const sendFn = vi.fn().mockResolvedValue(undefined);
    const throttler = new AdaptiveStreamThrottler(sendFn, {
      firstPacketDelayMs: 50,
      coalesceWindowMs: 250,
    });

    // First packet goes out fast
    throttler.push('1');
    await vi.advanceTimersByTimeAsync(50);
    expect(sendFn).toHaveBeenCalledWith('1', 1);

    // Subsequent packets debounce
    throttler.push('2');
    await vi.advanceTimersByTimeAsync(100);
    throttler.push('3');
    await vi.advanceTimersByTimeAsync(100);
    throttler.push('4');

    expect(sendFn).toHaveBeenCalledTimes(1); // Still only the first one

    await vi.advanceTimersByTimeAsync(250);

    // Should have dropped '2' and '3' and only sent '4'
    expect(sendFn).toHaveBeenCalledTimes(2);
    expect(sendFn).toHaveBeenLastCalledWith('4', 4);
  });

  it('flushNow sends immediately', async () => {
    const sendFn = vi.fn().mockResolvedValue(undefined);
    const throttler = new AdaptiveStreamThrottler(sendFn, { coalesceWindowMs: 250 });

    // First packet
    throttler.push('1');
    await vi.advanceTimersByTimeAsync(50);

    // Queue one up
    throttler.push('2');

    // Queue with flushNow
    throttler.push('3', { flushNow: true });

    expect(sendFn).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(0); // Immediately runs due to flushNow delay = 0
    expect(sendFn).toHaveBeenCalledTimes(2);
    expect(sendFn).toHaveBeenLastCalledWith('3', 3);
  });

  it('handles 429 rate limits with backoff', async () => {
    let sendCalls = 0;
    const sendFn = vi.fn().mockImplementation(() => {
      sendCalls++;
      if (sendCalls === 1) {
        return Promise.reject({ status: 429 });
      }
      return Promise.resolve(undefined);
    });

    const throttler = new AdaptiveStreamThrottler(sendFn, {
      firstPacketDelayMs: 50,
      baseBackoffMs: 100,
    });

    throttler.push('1');

    // Trigger first send which fails with 429
    await vi.advanceTimersByTimeAsync(50);

    expect(sendFn).toHaveBeenCalledTimes(1);

    // Should wait baseBackoffMs (100ms) for retry
    await vi.advanceTimersByTimeAsync(50);
    expect(sendFn).toHaveBeenCalledTimes(1);

    await vi.advanceTimersByTimeAsync(50);

    // Retry triggered
    expect(sendFn).toHaveBeenCalledTimes(2);
    expect(sendFn).toHaveBeenLastCalledWith('1', 1);
  });

  it('does not bypass backoff when new frame arrives, but sends new frame instead', async () => {
    let sendCalls = 0;
    const sendFn = vi.fn().mockImplementation(() => {
      sendCalls++;
      if (sendCalls === 1) {
        return Promise.reject({ status: 429 });
      }
      return Promise.resolve(undefined);
    });

    const throttler = new AdaptiveStreamThrottler(sendFn, {
      firstPacketDelayMs: 50,
      baseBackoffMs: 500,
      coalesceWindowMs: 100,
    });

    throttler.push('1');

    // Trigger first send which fails with 429
    await vi.advanceTimersByTimeAsync(50);
    expect(sendFn).toHaveBeenCalledTimes(1);

    // During 500ms backoff, a new frame arrives!
    await vi.advanceTimersByTimeAsync(100);
    throttler.push('2');

    // Wait out the rest of the 500ms backoff
    await vi.advanceTimersByTimeAsync(390);
    expect(sendFn).toHaveBeenCalledTimes(1); // Still waiting!

    await vi.advanceTimersByTimeAsync(10); // Now it should fire

    expect(sendFn).toHaveBeenCalledTimes(2);
    expect(sendFn).toHaveBeenLastCalledWith('2', 2);
  });

  it('flush resolves when everything is done, not prematurely', async () => {
    let resolveSend: () => void = () => {};
    let sendCount = 0;
    const sendFn = vi.fn().mockImplementation(() => {
      sendCount++;
      if (sendCount === 1) {
        return new Promise<void>(resolve => {
          resolveSend = resolve;
        });
      }
      return Promise.resolve();
    });

    const throttler = new AdaptiveStreamThrottler(sendFn, {
      firstPacketDelayMs: 50,
      coalesceWindowMs: 250,
    });

    throttler.push('1');
    await vi.advanceTimersByTimeAsync(50);

    expect(sendFn).toHaveBeenCalledTimes(1);

    // While 1 is in-flight, push 2 and call flush
    throttler.push('2');
    const flushPromise = throttler.flush();

    let isResolved = false;
    flushPromise.then(() => isResolved = true);

    // Resolve 1
    resolveSend();
    // Advance timers so the next scheduleSend gets picked up
    await vi.advanceTimersByTimeAsync(250);

    // Now flush should have triggered 2
    expect(sendFn).toHaveBeenCalledTimes(2); // 2 should have been sent

    // And flush should now resolve since 2 resolved immediately
    await vi.advanceTimersByTimeAsync(0);
    expect(isResolved).toBe(true);
  });


  it('flush during a 429 backoff does not clear backoff timer and eventually resolves', async () => {
    let sendCalls = 0;
    const sendFn = vi.fn().mockImplementation(() => {
      sendCalls++;
      if (sendCalls === 1) {
        return Promise.reject({ status: 429 });
      }
      return Promise.resolve(undefined);
    });

    const throttler = new AdaptiveStreamThrottler(sendFn, {
      firstPacketDelayMs: 50,
      baseBackoffMs: 500,
      coalesceWindowMs: 100,
    });

    throttler.push('1');

    // Trigger first send which fails with 429
    await vi.advanceTimersByTimeAsync(50);
    expect(sendFn).toHaveBeenCalledTimes(1);

    // Now we are in a 500ms backoff.
    // Call flush() or push({isFinal: true})
    throttler.push('2', { isFinal: true });
    const flushPromise = throttler.flush();

    let isResolved = false;
    flushPromise.then(() => isResolved = true);

    // It should NOT run immediately because we are in backoff!
    await vi.advanceTimersByTimeAsync(100);
    expect(sendFn).toHaveBeenCalledTimes(1);
    expect(isResolved).toBe(false);

    // Wait out the rest of the 500ms backoff
    await vi.advanceTimersByTimeAsync(400);

    // Now it should fire and resolve!
    expect(sendFn).toHaveBeenCalledTimes(2);
    expect(sendFn).toHaveBeenLastCalledWith('2', 2);

    // Allow Promise chain to resolve
    await vi.advanceTimersByTimeAsync(0);
    expect(isResolved).toBe(true);
  });
});

});
