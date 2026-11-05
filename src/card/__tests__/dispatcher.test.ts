import { describe, expect, it, vi } from 'vitest';
import { handleCardAction } from '../dispatcher';
import * as commands from '../../commands';
import type { CardDispatchDeps } from '../dispatcher';

vi.mock('../../commands', () => ({
  runCommandHandler: vi.fn().mockResolvedValue(true),
}));

describe('handleCardAction', () => {
  it('should debounce duplicate commands from the same user within 2 seconds', async () => {
    const operatorId = 'user123';
    const messageId = 'msg456';
    const cmd = 'stop';

    // Create mock deps
    const deps = {
      evt: {
        action: { value: { cmd } },
        operator: { openId: operatorId, name: 'Alice' },
        chatId: 'chat789',
        messageId,
      },
      channel: {} as any,
      sessions: {} as any,
      workspaces: {
        cwdFor: vi.fn().mockReturnValue(null),
      } as any,
      activeRuns: {} as any,
      agent: {} as any,
      controls: {
        profileConfig: {
          mode: 'personal',
          workspaces: {
            default: undefined,
          },
          access: {
            allowedUsers: [operatorId],
            admins: [],
          }
        },
      } as any,
      pending: {} as any,
      chatModeCache: {
        resolve: vi.fn().mockResolvedValue('p2p'),
      },
    } as unknown as CardDispatchDeps;

    // First call should proceed and call runCommandHandler
    await handleCardAction(deps);
    expect(commands.runCommandHandler).toHaveBeenCalledTimes(1);

    // Second call immediately after should be debounced and dropped
    await handleCardAction(deps);
    expect(commands.runCommandHandler).toHaveBeenCalledTimes(1);

    // Changing the messageId or cmd should bypass debounce
    const newDeps = {
      ...deps,
      evt: {
        ...deps.evt,
        action: { value: { cmd: 'reconnect' } },
      }
    } as unknown as CardDispatchDeps;

    await handleCardAction(newDeps);
    expect(commands.runCommandHandler).toHaveBeenCalledTimes(2);
  });
});
