import { smartChunkText } from './text-chunker';

export interface MobileSummaryCardOptions {
  botName?: string;
  summaryTitle?: string;
  detailTitle?: string;
  chunkMaxLength?: number;
}

/**
 * Builds a mobile-friendly high-density summary card.
 * Enforces a concise summary (max 3 lines) and puts the detailed data into
 * a collapsible panel to avoid screen flooding, while automatically chunking
 * long detailed text.
 */
export function buildMobileSummaryCard(
  summaryText: string,
  detailedText: string,
  options: MobileSummaryCardOptions = {}
): object {
  const botName = options.botName || 'AI 助手';
  const summaryTitle = options.summaryTitle || '📝 核心结论';
  const detailTitle = options.detailTitle || '🔍 详细数据 (点击展开)';
  const maxLength = options.chunkMaxLength || 3000;

  // 1. Process Summary (3 lines max)
  const summaryLines = (summaryText || '').split('\n').filter(line => line.trim().length > 0);
  const truncatedSummary = summaryLines.slice(0, 3).join('\n');
  const hasMoreSummary = summaryLines.length > 3;
  const finalSummaryText = hasMoreSummary ? `${truncatedSummary}\n... (更多结论见详情)` : truncatedSummary;

  const elements: object[] = [];

  // 2. Summary Block
  if (finalSummaryText.trim()) {
      elements.push({
          tag: 'markdown',
          content: `**${summaryTitle}**\n${finalSummaryText}`
      });
  }

  // 3. Detailed Data (in collapsible panel, chunked if necessary)
  const detailChunks = smartChunkText(detailedText || '无详细数据', maxLength);

  const detailElements = detailChunks.map(chunk => ({
      tag: 'markdown',
      content: chunk,
      text_size: 'notation'
  }));

  elements.push({
    tag: 'collapsible_panel',
    expanded: false, // Default to collapsed for mobile friendliness
    header: {
      title: {
        tag: 'markdown',
        content: `**${detailTitle}**`
      },
      vertical_align: 'center',
      icon: {
        tag: 'standard_icon',
        token: 'down-small-ccm_outlined',
        size: '16px 16px'
      },
      icon_position: 'follow_text',
      icon_expanded_angle: -180
    },
    border: {
        color: 'grey',
        corner_radius: '6px'
    },
    vertical_spacing: '8px',
    padding: '8px 8px 8px 8px',
    elements: detailElements.length > 0 ? detailElements : [{ tag: 'markdown', content: '_无输出_' }]
  });

  // 4. Return DSH Card 2.0 object
  return {
    schema: '2.0',
    config: {
      update_multi: true,
      wide_screen_mode: true
    },
    header: {
      template: 'blue',
      title: {
        tag: 'plain_text',
        content: `${botName} · 简报`
      }
    },
    body: {
      elements
    }
  };
}
