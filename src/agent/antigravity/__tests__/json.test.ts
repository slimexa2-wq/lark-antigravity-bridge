import { describe, expect, it } from 'vitest';
import { createAntigravityStreamState, translateAntigravityStreamLine } from '../json';

describe('translateAntigravityStreamLine', () => {
  it('should stringify object tool outputs safely', () => {
    const state = createAntigravityStreamState();

    // Simulate a successful stream line where tool output is an object instead of a string
    const input = {
      event: 'step_update',
      step_update: {
        step_type: 'tool',
        state: 'DONE',
        tool_info: {
          name: 'large_json_tool',
          output: { key1: 'value1', key2: 'value2', nested: { array: [1, 2, 3] } }
        }
      }
    };

    const events = translateAntigravityStreamLine(input, state);
    expect(events.length).toBeGreaterThan(0);
    const resultEvent = events.find(e => e.type === 'tool_result');
    expect(resultEvent).toBeDefined();

    // output should be safely stringified
    expect((resultEvent as any).output).toBe(JSON.stringify(input.step_update.tool_info.output));
  });

  it('should return empty string if object tool outputs cannot be stringified (e.g. circular)', () => {
    const state = createAntigravityStreamState();

    const circularObj: any = { key1: 'value1' };
    circularObj.circular = circularObj;

    const input = {
      event: 'step_update',
      step_update: {
        step_type: 'tool',
        state: 'DONE',
        tool_info: {
          name: 'bad_tool',
          output: circularObj
        }
      }
    };

    const events = translateAntigravityStreamLine(input, state);
    const resultEvent = events.find(e => e.type === 'tool_result');

    // output should be gracefully handled and set to empty string
    expect((resultEvent as any).output).toBe('');
  });
});
