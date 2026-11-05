import { existsSync, readFileSync } from 'node:fs';
import { createInterface } from 'node:readline';
import type { Readable } from 'node:stream';
import { homedir } from 'node:os';
import { join } from 'node:path';
import { log } from '../../core/logger';
import {
  mergeProcessEnv,
  spawnProcess,
  type SpawnedProcessByStdio,
} from '../../platform/spawn';
import { SpawnFailed } from '../../runtime/errors';
import { prefixBridgeSystemPrompt } from '../bridge-system-prompt';
import { buildLarkChannelEnv, type LarkChannelEnvContext } from '../lark-channel-env';
import { checkAgentAvailability, type AgentAvailability } from '../preflight';
import type {
  AgentAdapter,
  AgentBotIdentity,
  AgentEvent,
  AgentRun,
  AgentRunOptions,
} from '../types';
import {
  createAntigravityStreamState,
  translateAntigravityResult,
  translateAntigravityStreamLine,
} from './json';
import { findRemoteControlConversationUrl } from './remote-control';

export interface AntigravityAdapterOptions {
  binary: string;
  stopGraceMs?: number;
  larkChannel?: LarkChannelEnvContext;
  remoteControlLogDir?: string;
  outputFormat?: 'json' | 'stream-json';
}

type AntigravityChild = SpawnedProcessByStdio<null, Readable, Readable>;

export class AntigravityAdapter implements AgentAdapter {
  readonly id = 'antigravity';
  readonly displayName = 'Antigravity CLI';

  private readonly binary: string;
  private readonly defaultStopGraceMs: number;
  private readonly larkChannel: LarkChannelEnvContext | undefined;
  private readonly remoteControlLogDir: string | undefined;
  private readonly outputFormat: 'json' | 'stream-json';
  private botIdentity: AgentBotIdentity | undefined;

  constructor(opts: AntigravityAdapterOptions) {
    this.binary = opts.binary;
    this.defaultStopGraceMs = opts.stopGraceMs ?? 5000;
    this.larkChannel = opts.larkChannel;
    this.remoteControlLogDir =
      opts.remoteControlLogDir ??
      join(homedir(), '.gemini', 'antigravity-cli', 'log');
    this.outputFormat = opts.outputFormat ?? 'json';
  }

  setBotIdentity(identity: AgentBotIdentity): void {
    this.botIdentity = identity;
  }

  async isAvailable(): Promise<boolean> {
    return (await this.checkAvailability()).ok;
  }

  async checkAvailability(): Promise<AgentAvailability> {
    return checkAgentAvailability({
      agentId: 'antigravity',
      agentName: 'Antigravity CLI',
      command: this.binary,
      binaryPath: this.binary,
    });
  }

  async prepareRun(): Promise<void> {
    const availability = await this.checkAvailability();
    if (!availability.ok) {
      throw new SpawnFailed(
        'antigravity binary check failed',
        availability.error,
        availability.diagnostic.code,
        availability.diagnostic,
      );
    }
  }

  run(opts: AgentRunOptions): AgentRun {
    if (!opts.cwd) {
      throw new Error('cwd is required for AntigravityAdapter.run');
    }

    const prompt = prefixBridgeSystemPrompt(opts.prompt, this.botIdentity);
    const args = ['-p', prompt, '--output-format', this.outputFormat];

    if (opts.sessionId) {
      args.push('--conversation', opts.sessionId);
    }
    if (opts.model) {
      args.push('--model', opts.model);
    }
    if (
      opts.permissionMode === 'bypassPermissions' ||
      opts.sandbox === 'danger-full-access'
    ) {
      args.push('--dangerously-skip-permissions');
    } else if (opts.permissionMode === 'acceptEdits') {
      args.push('--mode', 'accept-edits');
    } else if (opts.permissionMode === 'plan') {
      args.push('--mode', 'plan');
    }

    const child = spawnProcess(this.binary, args, {
      cwd: opts.cwd,
      env: mergeProcessEnv(
        process.env,
        buildLarkChannelEnv(this.larkChannel),
      ),
      stdio: ['ignore', 'pipe', 'pipe'],
    }) as AntigravityChild;

    log.info('agent', 'spawn', {
      agent: 'antigravity',
      pid: child.pid ?? null,
      cwd: opts.cwd,
      promptChars: opts.prompt.length,
    });

    const stdoutChunks: Buffer[] = [];
    const stderrChunks: Buffer[] = [];
    let runtimeError: Error | null = null;
    let interrupted = false;

    child.stdout.on('data', (chunk: Buffer) => {
      stdoutChunks.push(chunk);
    });

    child.stderr.on('data', (chunk: Buffer) => {
      stderrChunks.push(chunk);
      const line = chunk.toString('utf8').trim();
      if (line) {
        log.warn('agent', 'stderr', {
          agent: 'antigravity',
          line: line.slice(0, 1000),
        });
      }
    });

    child.on('error', (err) => {
      runtimeError = err;
    });

    child.on('exit', (code, signal) => {
      log.info('agent', 'exit', {
        agent: 'antigravity',
        pid: child.pid ?? null,
        code,
        signal,
      });
    });

    const stopGraceMs = opts.stopGraceMs ?? this.defaultStopGraceMs;

    return {
      runId: opts.runId,

      events: createEventStream(
        child,
        stdoutChunks,
        stderrChunks,
        () => runtimeError,
        () => interrupted,
        this.remoteControlLogDir,
      ),

      async stop() {
        if (child.exitCode !== null || child.signalCode !== null) return;

        interrupted = true;

        log.info('agent', 'stop-sigterm', {
          agent: 'antigravity',
          pid: child.pid ?? null,
          graceMs: stopGraceMs,
        });

        child.kill('SIGTERM');

        await new Promise<void>((resolve) => {
          const timer = setTimeout(() => {
            if (child.exitCode === null && child.signalCode === null) {
              log.warn('agent', 'stop-sigkill', {
                agent: 'antigravity',
                pid: child.pid ?? null,
                graceMs: stopGraceMs,
              });
              child.kill('SIGKILL');
            }
            resolve();
          }, stopGraceMs);

          child.once('exit', () => {
            clearTimeout(timer);
            resolve();
          });
        });
      },

      waitForExit(timeoutMs: number): Promise<boolean> {
        if (child.exitCode !== null || child.signalCode !== null) {
          return Promise.resolve(true);
        }

        return new Promise<boolean>((resolve) => {
          const onExit = (): void => {
            clearTimeout(timer);
            resolve(true);
          };

          const timer = setTimeout(() => {
            child.removeListener('exit', onExit);
            resolve(false);
          }, timeoutMs);

          child.once('exit', onExit);
        });
      },
    };
  }
}

async function* createEventStream(
  child: AntigravityChild,
  stdoutChunks: Buffer[],
  stderrChunks: Buffer[],
  getRuntimeError: () => Error | null,
  wasInterrupted: () => boolean,
  remoteControlLogDir?: string,
): AsyncGenerator<AgentEvent> {
  if (!child.pid) {
    const err = getRuntimeError();
    yield {
      type: 'error',
      message: err
        ? `failed to spawn antigravity: ${err.message}`
        : 'spawn returned no pid',
      terminationReason: 'failed',
    };
    return;
  }

  const streamState = createAntigravityStreamState();
  let sawValidJsonLine = false;
  let sawNonEmptyLine = false;
  let turnMinStepIndex: number | undefined;
  const emittedThinkingSteps = new Set<number>();

  const rl = createInterface({ input: child.stdout, crlfDelay: Infinity });
  let sawStdout = false;
  let silentExitTimer: ReturnType<typeof setTimeout> | undefined;
  const closeSilentStdout = (): void => {
    silentExitTimer = setTimeout(() => {
      if (!sawStdout && !child.stdout.readableEnded) child.stdout.destroy();
    }, 50);
  };
  child.once('exit', closeSilentStdout);

  try {
    for await (const line of rl) {
      sawStdout = true;
      const trimmed = line.trim();
      if (!trimmed) continue;
      sawNonEmptyLine = true;

      let parsed: unknown;
      try {
        parsed = JSON.parse(trimmed);
        sawValidJsonLine = true;
      } catch {
        continue;
      }

      const translated = translateAntigravityStreamLine(parsed, streamState);

      if (parsed && typeof parsed === 'object') {
        const rawEvt = parsed as {
          event?: string;
          step_update?: { step_index?: number; step_type?: string; thinking_delta?: string };
        };
        if (rawEvt.event === 'step_update' && rawEvt.step_update) {
          const stepIdx = rawEvt.step_update.step_index;
          if (rawEvt.step_update.step_type === 'user_input' && typeof stepIdx === 'number') {
            turnMinStepIndex = stepIdx;
          } else if (turnMinStepIndex === undefined && typeof stepIdx === 'number') {
            turnMinStepIndex = Math.max(0, stepIdx - 1);
          }
          if (
            streamState.conversationId &&
            turnMinStepIndex !== undefined &&
            !rawEvt.step_update.thinking_delta
          ) {
            for (const thinkDelta of readNewTranscriptThinking(
              streamState.conversationId,
              turnMinStepIndex,
              emittedThinkingSteps,
            )) {
              yield { type: 'thinking', delta: thinkDelta };
            }
          }
        }
      }

      for (const evt of translated) {
        yield evt;
      }
    }
  } finally {
    if (silentExitTimer) clearTimeout(silentExitTimer);
    child.removeListener('exit', closeSilentStdout);
    rl.close();
  }

  const exitCode = await waitForExitCode(child);

  if (wasInterrupted()) {
    yield {
      type: 'done',
      terminationReason: 'interrupted',
    };
    return;
  }

  const runtimeError = getRuntimeError();
  if (runtimeError) {
    yield {
      type: 'error',
      message: `antigravity runtime error: ${runtimeError.message}`,
      terminationReason: 'failed',
    };
    return;
  }

  // Fallback for multi-line formatted JSON payload when readline didn't parse a single line
  if (!sawValidJsonLine && sawNonEmptyLine) {
    const fullStdout = Buffer.concat(stdoutChunks).toString('utf8').trim();
    if (fullStdout) {
      try {
        const parsed = JSON.parse(fullStdout);
        sawValidJsonLine = true;
        for (const evt of translateAntigravityStreamLine(parsed, streamState)) {
          yield evt;
        }
      } catch {
        // Handled below
      }
    }
  }

  const stderr = Buffer.concat(stderrChunks).toString('utf8').trim();

  const permissionMatch = stderr.match(
    /tool required the "([^"]+)" permission that headless mode cannot prompt for/i,
  );
  const deniedPermission = permissionMatch?.[1] ?? streamState.deniedPermission;

  if (deniedPermission) {
    const permission = deniedPermission || 'unknown';
    let conversationId = streamState.conversationId;

    if (!conversationId) {
      const stdout = Buffer.concat(stdoutChunks).toString('utf8').trim();
      if (stdout) {
        try {
          const parsed = JSON.parse(stdout) as { conversation_id?: unknown };
          if (
            typeof parsed.conversation_id === 'string' &&
            parsed.conversation_id.length > 0
          ) {
            conversationId = parsed.conversation_id;
          }
        } catch {
          // Ignore malformed stdout on permission failure
        }
      }
    }

    if (conversationId && !streamState.emittedSystem) {
      streamState.emittedSystem = true;
      yield {
        type: 'system',
        sessionId: conversationId,
      };
    }

    let remoteControlUrl: string | undefined;

    if (conversationId && remoteControlLogDir) {
      try {
        remoteControlUrl = await findRemoteControlConversationUrl(
          conversationId,
          remoteControlLogDir,
        );
      } catch (err) {
        log.warn('agent', 'remote-control-url', {
          agent: 'antigravity',
          error: err instanceof Error ? err.message : String(err),
        });
      }
    }

    yield {
      type: 'error',
      message: remoteControlUrl
        ? `Antigravity 权限不足：需要 ${permission} 权限；当前为 headless 模式，无法弹窗确认。请在 Antigravity Remote Control 中审批当前会话：${remoteControlUrl}`
        : `Antigravity 权限不足：需要 ${permission} 权限；当前为 headless 模式，无法弹窗确认。请打开 Antigravity Remote Control 查看对应会话；如需在 headless 模式自动执行，请为该命令配置 permissions.allow 后重试：https://antigravity.google.com`,
      terminationReason: 'failed',
    };
    return;
  }

  if (exitCode !== 0 && exitCode !== null) {
    const detail = stderr ? `: ${stderr.slice(0, 500)}` : '';

    yield {
      type: 'error',
      message: `antigravity exited with code ${exitCode}${detail}`,
      terminationReason: 'failed',
    };
    return;
  }

  if (!sawNonEmptyLine) {
    yield {
      type: 'error',
      message: 'antigravity returned empty stdout',
      terminationReason: 'failed',
    };
    return;
  }

  if (!sawValidJsonLine || !streamState.terminalResult) {
    yield {
      type: 'error',
      message: 'antigravity returned invalid JSON on stdout',
      terminationReason: 'failed',
    };
    return;
  }

  yield* translateAntigravityResult(streamState.terminalResult, {
    emittedSystem: streamState.emittedSystem,
    emittedStreamText: streamState.emittedStreamText,
  });
}

async function waitForExitCode(
  child: AntigravityChild,
): Promise<number | null> {
  if (child.exitCode !== null || child.signalCode !== null) {
    return child.exitCode;
  }

  return new Promise<number | null>((resolve) => {
    child.once('exit', (code) => resolve(code));
  });
}

function readNewTranscriptThinking(
  conversationId: string,
  minStepIndex: number,
  emittedSteps: Set<number>,
): string[] {
  if (!/^[a-f0-9-]+$/i.test(conversationId)) return [];
  const transcriptPath = join(
    homedir(),
    '.gemini',
    'antigravity-cli',
    'brain',
    conversationId,
    '.system_generated',
    'logs',
    'transcript.jsonl',
  );
  try {
    if (!existsSync(transcriptPath)) return [];
    const content = readFileSync(transcriptPath, 'utf8');
    const out: string[] = [];
    for (const line of content.split('\n')) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      try {
        const entry = JSON.parse(trimmed) as {
          step_index?: number;
          type?: string;
          thinking?: string;
        };
        if (
          typeof entry.step_index === 'number' &&
          entry.step_index >= minStepIndex &&
          entry.type === 'PLANNER_RESPONSE' &&
          typeof entry.thinking === 'string' &&
          entry.thinking.trim() &&
          !emittedSteps.has(entry.step_index)
        ) {
          emittedSteps.add(entry.step_index);
          out.push(`${entry.thinking.trim()}\n`);
        }
      } catch {
        // Ignore partial line
      }
    }
    return out;
  } catch {
    return [];
  }
}
