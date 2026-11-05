import type { AgentEvent } from '../types';

export interface AntigravityUsage {
  input_tokens?: number;
  output_tokens?: number;
  thinking_tokens?: number;
  cache_read_tokens?: number;
  total_tokens?: number;
}

export interface AntigravityDeniedAction {
  action?: string;
  display_name?: string;
}

export interface AntigravityResult {
  conversation_id?: string;
  status?: string;
  response?: string;
  duration_seconds?: number;
  num_turns?: number;
  usage?: AntigravityUsage;
  denied_actions?: AntigravityDeniedAction[];
}

export interface AntigravityStepToolInfo {
  name?: string;
  parameters?: unknown;
  output?: string;
  error?: {
    type?: string;
    message?: string;
  };
}

export interface AntigravityStepUpdate {
  conversation_id?: string;
  step_index?: number;
  state?: string;
  step_type?: string;
  text_delta?: string;
  thinking_delta?: string;
  tool_name?: string;
  duration_seconds?: number;
  tool_info?: AntigravityStepToolInfo;
  usage?: AntigravityUsage;
}

export interface AntigravityStreamEvent {
  event?: string;
  conversation_id?: string;
  init?: {
    cwd?: string;
    permission_mode?: string;
    tools?: string[];
  };
  step_update?: AntigravityStepUpdate;
  result?: AntigravityResult;
}

export interface AntigravityStreamTranslatorState {
  conversationId?: string;
  emittedSystem: boolean;
  emittedStreamText: boolean;
  startedTools: Set<string>;
  deniedPermission?: string;
  terminalResult?: AntigravityResult;
}

export function createAntigravityStreamState(): AntigravityStreamTranslatorState {
  return {
    emittedSystem: false,
    emittedStreamText: false,
    startedTools: new Set<string>(),
  };
}

export function translateAntigravityStreamLine(
  input: unknown,
  state: AntigravityStreamTranslatorState,
): AgentEvent[] {
  if (!input || typeof input !== 'object') return [];
  const raw = input as AntigravityStreamEvent & AntigravityResult;

  if (raw.event === 'init') {
    const events: AgentEvent[] = [];
    if (typeof raw.conversation_id === 'string' && raw.conversation_id.length > 0) {
      state.conversationId = raw.conversation_id;
      if (!state.emittedSystem) {
        state.emittedSystem = true;
        events.push({
          type: 'system',
          sessionId: raw.conversation_id,
          ...(typeof raw.init?.cwd === 'string' && raw.init.cwd ? { cwd: raw.init.cwd } : {}),
        });
      }
    }
    return events;
  }

  if (raw.event === 'step_update' && raw.step_update && typeof raw.step_update === 'object') {
    const step = raw.step_update;
    const events: AgentEvent[] = [];

    if (
      typeof step.conversation_id === 'string' &&
      step.conversation_id.length > 0 &&
      !state.emittedSystem
    ) {
      state.conversationId = step.conversation_id;
      state.emittedSystem = true;
      events.push({
        type: 'system',
        sessionId: step.conversation_id,
      });
    }

    if (typeof step.thinking_delta === 'string' && step.thinking_delta.length > 0) {
      events.push({
        type: 'thinking',
        delta: step.thinking_delta,
      });
    }

    if (step.step_type === 'tool') {
      const toolId = `step-${step.step_index ?? 0}`;
      const toolName = step.tool_name ?? step.tool_info?.name ?? 'tool';
      const toolInput = step.tool_info?.parameters ?? {};

      if (step.state === 'ACTIVE') {
        if (!state.startedTools.has(toolId)) {
          state.startedTools.add(toolId);
          events.push({
            type: 'tool_use',
            id: toolId,
            name: toolName,
            input: toolInput,
          });
        }
      } else if (
        step.state === 'DONE' ||
        step.state === 'ERROR' ||
        step.state === 'FAILED'
      ) {
        if (!state.startedTools.has(toolId)) {
          state.startedTools.add(toolId);
          events.push({
            type: 'tool_use',
            id: toolId,
            name: toolName,
            input: toolInput,
          });
        }
        const errMsg = step.tool_info?.error?.message;
        const output =
          typeof step.tool_info?.output === 'string'
            ? step.tool_info.output
            : typeof errMsg === 'string'
              ? errMsg
              : '';
        const isError = step.state !== 'DONE' || Boolean(step.tool_info?.error);
        events.push({
          type: 'tool_result',
          id: toolId,
          output,
          isError,
        });
      }
      return events;
    }

    if (step.step_type === 'agent_response') {
      if (typeof step.text_delta === 'string' && step.text_delta.length > 0) {
        state.emittedStreamText = true;
        events.push({
          type: 'text',
          delta: step.text_delta,
        });
      }
    }

    return events;
  }

  if (raw.event === 'result' && raw.result && typeof raw.result === 'object') {
    if (
      typeof raw.result.conversation_id === 'string' &&
      raw.result.conversation_id.length > 0
    ) {
      state.conversationId = raw.result.conversation_id;
    }
    if (Array.isArray(raw.result.denied_actions) && raw.result.denied_actions.length > 0) {
      const firstDenied = raw.result.denied_actions[0];
      state.deniedPermission = firstDenied?.action ?? 'command';
    }
    state.terminalResult = raw.result;
    return [];
  }

  // Fallback: single-line JSON output (`--output-format json`)
  if (typeof raw.status === 'string' || typeof raw.conversation_id === 'string') {
    if (typeof raw.conversation_id === 'string' && raw.conversation_id.length > 0) {
      state.conversationId = raw.conversation_id;
    }
    if (Array.isArray(raw.denied_actions) && raw.denied_actions.length > 0) {
      const firstDenied = raw.denied_actions[0];
      state.deniedPermission = firstDenied?.action ?? 'command';
    }
    state.terminalResult = raw;
  }

  return [];
}

export function translateAntigravityResult(
  input: unknown,
  options: {
    emittedSystem?: boolean;
    emittedStreamText?: boolean;
  } = {},
): AgentEvent[] {
  if (!input || typeof input !== 'object') {
    return [
      {
        type: 'error',
        message: 'antigravity returned invalid JSON payload',
        terminationReason: 'failed',
      },
    ];
  }

  const result = input as AntigravityResult;
  const hasRecoveredResponse =
    Boolean(options.emittedStreamText) ||
    (typeof result.response === 'string' && result.response.trim().length > 0);
  const hasDeniedActions =
    Array.isArray(result.denied_actions) && result.denied_actions.length > 0;

  if (result.status !== 'SUCCESS' && (!hasRecoveredResponse || hasDeniedActions)) {
    return [
      {
        type: 'error',
        message: `antigravity run failed${result.status ? `: ${result.status}` : ''}`,
        terminationReason: 'failed',
      },
    ];
  }

  const events: AgentEvent[] = [];

  if (
    !options.emittedSystem &&
    typeof result.conversation_id === 'string' &&
    result.conversation_id.length > 0
  ) {
    events.push({
      type: 'system',
      sessionId: result.conversation_id,
    });
  }

  if (
    !options.emittedStreamText &&
    typeof result.response === 'string' &&
    result.response.length > 0
  ) {
    events.push({
      type: 'final_text',
      content: result.response,
    });
  }

  if (result.usage) {
    events.push({
      type: 'usage',
      ...(typeof result.usage.input_tokens === 'number'
        ? { inputTokens: result.usage.input_tokens }
        : {}),
      ...(typeof result.usage.output_tokens === 'number'
        ? { outputTokens: result.usage.output_tokens }
        : {}),
      ...(typeof result.usage.cache_read_tokens === 'number'
        ? { cachedInputTokens: result.usage.cache_read_tokens }
        : {}),
      ...(typeof result.usage.thinking_tokens === 'number'
        ? { reasoningOutputTokens: result.usage.thinking_tokens }
        : {}),
    });
  }

  events.push({
    type: 'done',
    terminationReason: 'normal',
  });

  return events;
}
