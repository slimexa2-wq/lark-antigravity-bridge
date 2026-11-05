import { describe, expect, it } from 'vitest';
import { renderCard } from '../run-renderer';
import type { RunState } from '../run-state';

describe('renderCard', () => {
  it('should include update_multi: true in basic card config', () => {
    const state: RunState = {
      terminal: 'running',
      blocks: [],
      footer: null,
      reasoning: { active: false, content: '' },
    };

    const rendered: any = renderCard(state);
    expect(rendered.config).toBeDefined();
    expect(rendered.config.update_multi).toBe(true);
  });

  it('should render a reconnect button when state.terminal is error', () => {
    const state: RunState = {
      terminal: 'error',
      errorMsg: 'Agent crashed',
      blocks: [],
      footer: null,
      reasoning: { active: false, content: '' },
    };

    // Testing basic card
    const renderedBasic: any = renderCard(state);

    // In basic card, body.elements should have a markdown for error and a button for reconnect
    const basicElements = renderedBasic.body.elements;
    const basicReconnectBtn = basicElements.find((e: any) =>
      e.tag === 'button' && e.behaviors?.[0]?.value?.cmd === 'reconnect'
    );
    expect(basicReconnectBtn).toBeDefined();
    expect(basicReconnectBtn.text.content).toContain('异常重连');

    // Testing rich card
    const renderedRich: any = renderCard(state, { richCard: true });
    const richElements = renderedRich.body.elements;
    const richReconnectBtn = richElements.find((e: any) =>
      e.tag === 'button' && e.behaviors?.[0]?.value?.cmd === 'reconnect'
    );
    expect(richReconnectBtn).toBeDefined();
    expect(richReconnectBtn.text.content).toContain('异常重连');
  });
});
