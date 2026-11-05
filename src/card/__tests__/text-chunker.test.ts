import { describe, expect, it } from 'vitest';
import { smartChunkText } from '../text-chunker';

describe('smartChunkText', () => {
  it('should return empty array for empty string', () => {
    expect(smartChunkText('')).toEqual([]);
  });

  it('should return single chunk if text is shorter than maxLength', () => {
    const text = 'Hello world!';
    const chunks = smartChunkText(text, 50);
    expect(chunks).toEqual([text]);
    expect(chunks.length).toBe(1);
  });

  it('should split by double newline', () => {
    const text = 'Paragraph 1\n\nParagraph 2\n\nParagraph 3';
    // maxLength 20 ensures we split at the first double newline (index ~11)
    const chunks = smartChunkText(text, 20);
    expect(chunks.length).toBe(3);
    expect(chunks[0]).toBe('Paragraph 1');
    expect(chunks[1]).toBe('Paragraph 2');
    expect(chunks[2]).toBe('Paragraph 3');
  });

  it('should fallback to single newline if double newline not found', () => {
    const text = 'Line 1\nLine 2\nLine 3';
    const chunks = smartChunkText(text, 10);
    expect(chunks.length).toBe(3);
    expect(chunks[0]).toBe('Line 1');
    expect(chunks[1]).toBe('Line 2');
    expect(chunks[2]).toBe('Line 3');
  });

  it('should fallback to space if no newlines found', () => {
    const text = 'word1 word2 word3';
    const chunks = smartChunkText(text, 10);
    expect(chunks.length).toBe(3);
    expect(chunks[0]).toBe('word1');
    expect(chunks[1]).toBe('word2');
    expect(chunks[2]).toBe('word3');
  });

  it('should hard split if no spaces or newlines found', () => {
    const text = 'verylongstringwithoutanyspacesornewlines';
    const chunks = smartChunkText(text, 10);
    expect(chunks.length).toBe(4);
    expect(chunks[0]).toBe('verylongst');
    expect(chunks[1]).toBe('ringwithou');
    expect(chunks[2]).toBe('tanyspaces');
    expect(chunks[3]).toBe('ornewlines');
  });
});
