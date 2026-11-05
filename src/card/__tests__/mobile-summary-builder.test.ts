import { describe, expect, it } from 'vitest';
import { buildMobileSummaryCard } from '../mobile-summary-builder';

describe('buildMobileSummaryCard', () => {
  it('should build a card with truncated summary and collapsible details', () => {
    const summaryText = 'Line 1\nLine 2\nLine 3\nLine 4';
    const detailedText = 'Some detailed information...';

    const card: any = buildMobileSummaryCard(summaryText, detailedText, { botName: 'TestBot' });

    expect(card.schema).toBe('2.0');
    expect(card.header.title.content).toBe('TestBot · 简报');

    const elements = card.body.elements;
    expect(elements.length).toBe(2);

    // Summary block (should be max 3 lines + more indication)
    const summaryBlock = elements[0];
    expect(summaryBlock.tag).toBe('markdown');
    expect(summaryBlock.content).toContain('Line 1\nLine 2\nLine 3\n... (更多结论见详情)');

    // Detail block (should be collapsible panel)
    const detailBlock = elements[1];
    expect(detailBlock.tag).toBe('collapsible_panel');
    expect(detailBlock.expanded).toBe(false); // Collapsed by default for mobile
    expect(detailBlock.elements.length).toBe(1);
    expect(detailBlock.elements[0].content).toBe(detailedText);
  });

  it('should not add "more" indication if summary is 3 lines or less', () => {
    const summaryText = 'Line 1\nLine 2';
    const detailedText = 'Details';

    const card: any = buildMobileSummaryCard(summaryText, detailedText);
    const summaryBlock = card.body.elements[0];

    expect(summaryBlock.content).not.toContain('更多结论见详情');
    expect(summaryBlock.content).toContain('Line 1\nLine 2');
  });

  it('should auto-chunk long detailed text inside the collapsible panel', () => {
    const summaryText = 'Short summary';
    // Create a detailed text that will be chunked (e.g. 50 characters, chunkMaxLength = 20)
    const detailedText = 'A very long detail text that needs to be chunked into multiple parts';

    const card: any = buildMobileSummaryCard(summaryText, detailedText, { chunkMaxLength: 20 });
    const detailBlock = card.body.elements[1];

    // Expect multiple chunks due to the short chunkMaxLength
    expect(detailBlock.elements.length).toBeGreaterThan(1);
    expect(detailBlock.elements[0].tag).toBe('markdown');
    expect(detailBlock.elements[0].text_size).toBe('notation');
  });

  it('should handle empty detailed text gracefully', () => {
    const card: any = buildMobileSummaryCard('Summary', '');
    const detailBlock = card.body.elements[1];

    expect(detailBlock.elements[0].content).toBe('无详细数据');
  });
});
