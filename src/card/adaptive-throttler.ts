import { log } from '../core/logger';

export class SequenceLock {
  private currentSequence = 0;

  public acquire(seq: number): boolean {
    if (seq > this.currentSequence) {
      this.currentSequence = seq;
      return true;
    }
    return false;
  }

  public current(): number {
    return this.currentSequence;
  }

  public getNext(): number {
    return this.currentSequence + 1;
  }
}

export interface ThrottlerOptions {
  firstPacketDelayMs?: number;
  coalesceWindowMs?: number;
  maxRetries?: number;
  baseBackoffMs?: number;
}

export class AdaptiveStreamThrottler<T> {
  private readonly sequenceLock = new SequenceLock();
  private readonly firstPacketDelayMs: number;
  private readonly coalesceWindowMs: number;
  private readonly maxRetries: number;
  private readonly baseBackoffMs: number;

  private timer: ReturnType<typeof setTimeout> | null = null;
  private isFirstPacket = true;
  private nextFrame: { data: T, seq: number, isFinal: boolean, flushNow: boolean } | null = null;
  private isInFlight = false;
  private isBackingOff = false;

  private resolveFlush: Array<() => void> = [];

  constructor(
    private readonly sendFn: (data: T, seq: number) => Promise<void>,
    options?: ThrottlerOptions
  ) {
    this.firstPacketDelayMs = options?.firstPacketDelayMs ?? 50;
    this.coalesceWindowMs = options?.coalesceWindowMs ?? 250;
    this.maxRetries = options?.maxRetries ?? 3;
    this.baseBackoffMs = options?.baseBackoffMs ?? 500;
  }

  public push(data: T, options?: { flushNow?: boolean; isFinal?: boolean }): void {
    const seq = this.sequenceLock.getNext();
    this.sequenceLock.acquire(seq);

    this.nextFrame = {
        data,
        seq,
        isFinal: options?.isFinal ?? false,
        flushNow: options?.flushNow ?? false
    };

    if (options?.flushNow || options?.isFinal) {
      this.scheduleSend(0);
    } else if (!this.timer) {
      const delay = this.isFirstPacket ? this.firstPacketDelayMs : this.coalesceWindowMs;
      this.scheduleSend(delay);
    }
  }

  private scheduleSend(delay: number) {
    // If we are in a backoff period, we must not override the backoff timer.
    // The backoff timer will trigger processNext() when ready.
    if (this.isBackingOff) {
        return;
    }

    if (this.timer) {
      clearTimeout(this.timer);
    }
    this.timer = setTimeout(() => this.processNext(), delay);
  }

  private async processNext(retries = 0): Promise<void> {
    this.timer = null;
    this.isBackingOff = false;

    if (!this.nextFrame || this.isInFlight) {
      return;
    }

    const frame = this.nextFrame;
    this.nextFrame = null;
    this.isInFlight = true;

    try {
      await this.sendFn(frame.data, frame.seq);
      this.isFirstPacket = false;
      this.isInFlight = false;

      if (this.nextFrame) {
        // If a flush was requested or this is the final frame, send it immediately
        const delay = (this.resolveFlush.length > 0 || this.nextFrame.flushNow || this.nextFrame.isFinal) ? 0 : this.coalesceWindowMs;
        this.scheduleSend(delay);
      } else {
        this.resolveFlushPromises();
      }
    } catch (err: any) {
      const isRateLimit = err?.response?.status === 429 || err?.status === 429 || err?.code === 429 || (err.message && err.message.includes('429'));

      if (isRateLimit && retries < this.maxRetries) {
        log.warn('adaptive-throttler', 'Rate limited, retrying', { retries, seq: frame.seq });

        if (!this.nextFrame || frame.seq > this.nextFrame.seq) {
            this.nextFrame = frame;
        }

        this.isInFlight = false;
        this.isBackingOff = true;

        const backoffMs = this.baseBackoffMs * Math.pow(2, retries);
        this.timer = setTimeout(() => {
          this.processNext(retries + 1);
        }, backoffMs);

      } else {
        log.error('adaptive-throttler', 'Failed to send frame', { err, seq: frame.seq, retries });
        this.isInFlight = false;

        if (this.nextFrame) {
          const delay = (this.resolveFlush.length > 0 || this.nextFrame.flushNow || this.nextFrame.isFinal) ? 0 : this.coalesceWindowMs;
          this.scheduleSend(delay);
        } else {
          this.resolveFlushPromises();
        }
      }
    }
  }

  private resolveFlushPromises() {
      const resolvers = this.resolveFlush;
      this.resolveFlush = [];
      for (const r of resolvers) {
          r();
      }
  }

  public async flush(): Promise<void> {
    if (!this.nextFrame && !this.isInFlight && !this.timer) {
      return Promise.resolve();
    }

    if (this.nextFrame) {
        this.scheduleSend(0);
    }

    return new Promise((resolve) => {
        this.resolveFlush.push(resolve);
    });
  }
}
