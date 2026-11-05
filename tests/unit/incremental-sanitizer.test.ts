import { describe, expect, it } from 'vitest';
import { IncrementalMarkdownAndJsonRepair } from '../../src/utils/incremental-sanitizer';

describe('IncrementalMarkdownAndJsonRepair', () => {
  describe('sanitizeMarkdown', () => {
    it('should not alter normal text', () => {
      const text = 'Hello world\nThis is a test.';
      expect(IncrementalMarkdownAndJsonRepair.sanitizeMarkdown(text)).toBe(text);
    });

    it('should close unclosed markdown code blocks', () => {
      const text = 'Here is some code:\n```typescript\nconst a = 1;';
      const expected = 'Here is some code:\n```typescript\nconst a = 1;\n```';
      expect(IncrementalMarkdownAndJsonRepair.sanitizeMarkdown(text)).toBe(expected);
    });

    it('should handle unclosed markdown code blocks with tildes', () => {
      const text = '~~~bash\necho "Hello"';
      const expected = '~~~bash\necho "Hello"\n~~~';
      expect(IncrementalMarkdownAndJsonRepair.sanitizeMarkdown(text)).toBe(expected);
    });

    it('should not append marker if code block is already closed', () => {
      const text = '```\nclosed\n```\nmore text';
      expect(IncrementalMarkdownAndJsonRepair.sanitizeMarkdown(text)).toBe(text);
    });

    it('should close an unclosed table at the end', () => {
      const text = '| Col 1 | Col 2 |\n| --- | --- |\n| row1 | val1';
      const expected = '| Col 1 | Col 2 |\n| --- | --- |\n| row1 | val1 |';
      expect(IncrementalMarkdownAndJsonRepair.sanitizeMarkdown(text)).toBe(expected);
    });

    it('should not alter a closed table', () => {
      const text = '| Col 1 | Col 2 |\n| --- | --- |\n| row1 | val1 |';
      expect(IncrementalMarkdownAndJsonRepair.sanitizeMarkdown(text)).toBe(text);
    });
  });

  describe('sanitizeJson', () => {
    it('should parse complete JSON successfully', () => {
      const jsonStr = '{"a": 1, "b": [1, 2]}';
      expect(IncrementalMarkdownAndJsonRepair.sanitizeJson(jsonStr)).toBe(jsonStr);
    });

    it('should close an unclosed string', () => {
      const jsonStr = '{"a": "hello';
      const expected = '{"a": "hello"}';
      expect(IncrementalMarkdownAndJsonRepair.sanitizeJson(jsonStr)).toBe(expected);
    });

    it('should remove trailing comma', () => {
      const jsonStr = '{"a": 1, "b": 2,';
      const expected = '{"a": 1, "b": 2}';
      expect(IncrementalMarkdownAndJsonRepair.sanitizeJson(jsonStr)).toBe(expected);
    });

    it('should close an unclosed array and object', () => {
      const jsonStr = '{"a": [1, 2, {"b": "value"';
      const expected = '{"a": [1, 2, {"b": "value"}]}';
      expect(IncrementalMarkdownAndJsonRepair.sanitizeJson(jsonStr)).toBe(expected);
    });
  });
});
