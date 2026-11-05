import { basename } from 'node:path';
import { deepMaskEmails } from './mask-email';
import type { Block, FooterStatus, RunState, ToolEntry } from './run-state';
import { toolBodyMd, toolHeaderText } from './tool-render';
import { IncrementalMarkdownAndJsonRepair } from '../utils/incremental-sanitizer';

const REASONING_MAX = 1500;
const COLLAPSE_TOOL_THRESHOLD = 3;
const MAX_MARKDOWN_ELEMENT_CHARS = 3200;

interface ToolGroup {
  kind: 'tools';
  tools: ToolEntry[];
}
interface TextGroup {
  kind: 'text';
  content: string;
}
type Group = ToolGroup | TextGroup;

export interface RunCardRenderOptions {
  signCallback?: (action: string) => string;
  richCard?: boolean;
  botName?: string;
}

export function renderCard(state: RunState, options: RunCardRenderOptions = {}): object {
  return renderRichCard(state, options);
  const elements: object[] = [];

  if (state.reasoning.content) {
    elements.push(reasoningPanel(state.reasoning.content, state.reasoning.active));
  }

  for (const group of groupBlocks(state.blocks)) {
    if (group.kind === 'text') {
      if (group.content.trim()) {
        elements.push(markdown(group.content));
      }
    } else {
      elements.push(...renderToolGroup(group.tools, state.terminal !== 'running'));
    }
  }

  if (state.terminal === 'interrupted') {
    elements.push(noteMd('_⏹ 已被中断_'));
  } else if (state.terminal === 'idle_timeout') {
    const mins = state.idleTimeoutMinutes ?? 0;
    elements.push(noteMd(`_⏱ ${mins} 分钟无响应,已自动终止_`));
  } else if (state.terminal === 'error' && state.errorMsg) {
    elements.push(noteMd(`⚠️ agent 失败：${state.errorMsg}`));
    elements.push(reconnectButton(options));
  } else if (state.terminal === 'done' && elements.length === 0) {
    elements.push(noteMd('_（未返回内容）_'));
  }

  if (state.terminal === 'running') {
    if (state.footer) elements.push(footerStatus(state.footer));
    elements.push({ tag: 'action', actions: [stopButton(options)] });
  } else if (state.terminal === 'done') {
    elements.push(undoButton(options));
  }

  // Mask raw emails across every text field so the Feishu tenant audit doesn't
  // reject the (streamed) card with a 400 EMAIL_ADDRESS — see mask-email.ts.
  return deepMaskEmails({
    schema: '2.0',
    config: {
      update_multi: true,
      streaming_mode: state.terminal === 'running',
      summary: { content: summaryText(state) },
    },
    body: { elements },
  });
}

function* groupBlocks(blocks: Block[]): Generator<Group> {
  let toolBuf: ToolEntry[] = [];
  for (const b of blocks) {
    if (b.kind === 'tool') {
      toolBuf.push(b.tool);
    } else {
      if (toolBuf.length > 0) {
        yield { kind: 'tools', tools: toolBuf };
        toolBuf = [];
      }
      yield { kind: 'text', content: b.content };
    }
  }
  if (toolBuf.length > 0) yield { kind: 'tools', tools: toolBuf };
}

function renderToolGroup(tools: ToolEntry[], finalized: boolean): object[] {
  if (tools.length === 0) return [];
  if (tools.length < COLLAPSE_TOOL_THRESHOLD) {
    return tools.map((t) => toolPanel(t, false));
  }
  if (finalized) {
    return [collapsedToolSummary(tools, true)];
  }
  // Running: collapse prior tools, keep latest visible.
  const prior = tools.slice(0, -1);
  const latest = tools[tools.length - 1];
  const out: object[] = [];
  if (prior.length > 0) out.push(collapsedToolSummary(prior, false));
  if (latest) out.push(toolPanel(latest, true));
  return out;
}

function reasoningPanel(content: string, active: boolean): object {
  const title = active ? '🧠 **思考中**' : '🧠 **思考完成，点击查看**';
  return collapsiblePanel({
    title,
    expanded: active,
    border: 'grey',
    body: truncate(content, REASONING_MAX),
  });
}

function toolPanel(tool: ToolEntry, expanded: boolean): object {
  return collapsiblePanel({
    title: toolHeaderText(tool),
    expanded,
    border: tool.status === 'error' ? 'red' : 'grey',
    body: toolBodyMd(tool) || '_无输出_',
  });
}

/**
 * Render N tool calls as a single collapsed panel. **Body content is dropped**
 * — only the per-tool header line (icon + name + short summary) is kept.
 *
 * Why no bodies: with full input/output panels nested, the serialized JSON
 * can easily exceed Feishu's per-element size limit (~30KB), causing 400
 * errors that abort the entire card stream. Tool details are still in the
 * file log; users who really need them can `/doctor` to inspect.
 *
 * The latest-running tool, when applicable, is rendered separately via
 * `toolPanel(latest, true)` so live observation isn't sacrificed.
 */
function collapsedToolSummary(tools: ToolEntry[], finalized: boolean): object {
  const suffix = finalized ? '（已结束）' : '';
  const title = `☕ **${tools.length} 个工具调用${suffix}**`;
  const headerList = tools.map((t) => `- ${toolHeaderText(t)}`).join('\n');
  return {
    tag: 'collapsible_panel',
    expanded: false,
    header: panelHeader(title),
    border: { color: 'blue', corner_radius: '5px' },
    vertical_spacing: '8px',
    padding: '8px 8px 8px 8px',
    elements: [{ tag: 'markdown', content: headerList, text_size: 'notation' }],
  };
}

interface PanelOpts {
  title: string;
  expanded: boolean;
  border: 'grey' | 'red' | 'blue';
  body: string;
}

function collapsiblePanel(opts: PanelOpts): object {
  return {
    tag: 'collapsible_panel',
    expanded: opts.expanded,
    header: panelHeader(opts.title),
    border: { color: opts.border, corner_radius: '5px' },
    vertical_spacing: '8px',
    padding: '8px 8px 8px 8px',
    elements: [{ tag: 'markdown', content: opts.body, text_size: 'notation' }],
  };
}

function panelHeader(titleMd: string): object {
  return {
    title: { tag: 'markdown', content: titleMd },
    vertical_align: 'center',
    icon: { tag: 'standard_icon', token: 'down-small-ccm_outlined', size: '16px 16px' },
    icon_position: 'follow_text',
    icon_expanded_angle: -180,
  };
}

function markdown(content: string): object {
  return { tag: 'markdown', content };
}

function noteMd(content: string): object {
  return { tag: 'markdown', content, text_size: 'notation' };
}

function stopButton(options: RunCardRenderOptions): object {
  const value: Record<string, unknown> = { cmd: 'stop' };
  if (options.signCallback) {
    value.__bridge_cb = true;
    value.bridge_token = options.signCallback('stop');
  }
  return {
    tag: 'button',
    text: { tag: 'plain_text', content: '⏹ 终止' },
    type: 'danger',
    behaviors: [{ type: 'callback', value }],
  };
}

function reconnectButton(options: RunCardRenderOptions): object {
  const value: Record<string, unknown> = { cmd: 'reconnect' };
  if (options.signCallback) {
    value.__bridge_cb = true;
    value.bridge_token = options.signCallback('reconnect');
  }
  return {
    tag: 'button',
    text: { tag: 'plain_text', content: '🔄 异常重连' },
    type: 'primary',
    behaviors: [{ type: 'callback', value }],
  };
}

function footerStatus(status: Exclude<FooterStatus, null>): object {
  const text =
    status === 'thinking'
      ? '🧠 正在思考'
      : status === 'tool_running'
        ? '🧰 正在调用工具'
        : '✍️ 正在输出';
  return noteMd(text);
}

function summaryText(state: RunState): string {
  if (state.terminal === 'interrupted') return '已中断';
  if (state.terminal === 'idle_timeout') return '已超时';
  if (state.terminal === 'error') return '出错';
  if (state.terminal === 'done') return '已完成';
  if (state.footer === 'tool_running') return '正在调用工具';
  if (state.footer === 'streaming') return '正在输出';
  return '思考中';
}

function truncate(s: string, max: number): string {
  return s.length > max ? `${s.slice(0, max)}…` : s;
}

/**
 * 清洗并规范化飞书卡片 Markdown（DSH Card 2.0 规范）：
 * - 将本地路径链接 [label](file:///Users/...) 简化为纯文件名或标签
 * - 将裸露的本地绝对路径 /Users/... 简化为文件名 **xxx.ext**
 * - 移除冗长的 SHA256 哈希串
 * - 将行内反引号 `code` 转为加粗 **code**，规避飞书 lark_md 将反引号内 `-` 渲染为 `&#45;`
 */
export function normalizeFeishuMarkdown(raw: string): string {
  let text = String(raw || '').trim();
  if (!text) return '';

  // 1. Replace [label](file:///Users/...) or [label](/Users/...) with clean label/basename
  text = text.replace(
    /\[([^\]]+)\]\((?:file:\/\/)?(\/(?:Users|tmp|private|var)\/[^)\s]+)\)/g,
    (_, label: string, filePath: string) => {
      const base = basename(filePath.replace(/#L\d+.*$/, ''));
      const cleanLabel = label.trim().replace(/^`|`$/g, '');
      if (!cleanLabel || cleanLabel === base || cleanLabel.startsWith('/Users/')) {
        return `**${base}**`;
      }
      return `**${cleanLabel}**（${base}）`;
    },
  );

  // 2. Replace bare file:///Users/... or /Users/... paths with just the basename
  text = text.replace(
    /(?:file:\/\/)?\/(?:Users|tmp|private|var)\/[^\s)`"'<>，。；：、|\]]+/g,
    (match: string) => {
      const clean = match.replace(/#L\d+.*$/, '');
      const base = basename(clean);
      return base ? `**${base}**` : '';
    },
  );

  // 3. Strip standalone SHA256 labels/hashes
  text = text.replace(/\b(?:sha256|SHA-?256)\s*[:：=]?\s*[a-f0-9]{16,64}\b/gi, '');
  text = text.replace(/\b[a-f0-9]{40,64}\b/g, '');

  // 4. Convert ### / ## / # headings to clean visual anchors
  text = text
    .replace(/^#{1,2}\s+(.+)$/gm, '\n**▍ $1**')
    .replace(/^#{3,6}\s+(.+)$/gm, '**• $1**');

  // Collapse excessive blank lines
  text = text.replace(/\n{3,}/g, '\n\n');
  return text.trim();
}

function normalizeThinkingSmallText(raw: string): string {
  let text = normalizeFeishuMarkdown(raw);
  if (!text) return '';
  text = text
    .replace(/[<>]/g, '')
    .replace(/\n{2,}/g, '\n')
    .trim();
  if (text.length > 1000) {
    text = `…${text.slice(-1000)}`;
  }
  return text;
}

function buildRichThinkingAndToolsPanel(state: RunState): object | null {
  const isStreaming = state.terminal === 'running';
  const tools: ToolEntry[] = [];
  for (const b of state.blocks) {
    if (b.kind === 'tool') tools.push(b.tool);
  }
  const hasReasoning = Boolean(state.reasoning.content.trim());

  const lines: string[] = [];
  if (hasReasoning) {
    const cleanReasoning = normalizeThinkingSmallText(state.reasoning.content);
    for (const rLine of cleanReasoning.split('\n').filter(Boolean)) {
      lines.push(rLine.startsWith('•') || rLine.startsWith('💭') ? rLine : `💭 ${rLine}`);
    }
  }

  for (const t of tools) {
    const cleanHeader = normalizeThinkingSmallText(toolHeaderText(t));
    if (cleanHeader) {
      lines.push(`• ${cleanHeader}`);
    }
  }

  if (lines.length === 0) {
    lines.push(
      isStreaming
        ? '• 已接收飞书指令，正在唤醒 Antigravity 分析与执行…'
        : '• 已完成指令解析与推理汇总',
    );
  }

  const stepCount = Math.max(1, tools.length + (hasReasoning ? 1 : 0));
  const headerTitle = isStreaming
    ? '🧠 <font color="grey">思考与执行过程（正在处理… 完成后自动收起）</font>'
    : `💭 <font color="grey">思考与执行过程（共 ${stepCount} 步 · 已收起，点击下拉查看）</font>`;

  const bodyText = lines.slice(-14).join('\n');

  return {
    tag: 'collapsible_panel',
    expanded: isStreaming,
    background_color: 'grey',
    header: {
      title: {
        tag: 'markdown',
        text_size: 'notation',
        content: headerTitle,
      },
      vertical_align: 'center',
      icon: {
        tag: 'standard_icon',
        token: 'down-small-ccm_outlined',
        size: '14px 14px',
      },
      icon_position: 'right',
      icon_expanded_angle: -180,
    },
    border: {
      color: 'grey',
      corner_radius: '6px',
    },
    vertical_spacing: '4px',
    padding: '6px 10px 6px 10px',
    elements: [
      {
        tag: 'markdown',
        text_size: 'notation',
        content: `<font color="grey">${bodyText}</font>`,
      },
    ],
  };
}

function isTableSeparatorLine(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed.startsWith('|') || !trimmed.endsWith('|')) return false;
  const cells = trimmed
    .slice(1, -1)
    .split('|')
    .map((c) => c.trim());
  return cells.length >= 2 && cells.every((c) => /^:?-{2,}:?$/.test(c));
}

function splitTableRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '');
  return trimmed.split('|').map((c) => normalizeFeishuMarkdown(c.trim()));
}

function decorateCellVisuals(cellText: string | undefined): string {
  const raw = String(cellText || '').trim();
  if (!raw) return '-';
  const plain = raw.replace(/\*\*/g, '').replace(/`/g, '').trim();
  if (/^(?:🟢|🔵|🟠|🔴|✅|⚠️|❌)/.test(plain)) return raw;
  if (/^(?:通过|已通过|正常|完成|已完成|达标|已达标|在线|就绪|成功|已启用|已连接|PASS|OK)$/i.test(plain)) {
    return `🟢 ${raw}`;
  }
  if (/^(?:待确认|待拍板|进行中|处理中|部分完成|预警|WARN|PENDING)$/i.test(plain)) {
    return `🟠 ${raw}`;
  }
  if (/^(?:失败|异常|未通过|阻断|超标|错误|未连接|FAIL|ERROR|BLOCKED)$/i.test(plain)) {
    return `🔴 ${raw}`;
  }
  return raw;
}

function renderVisualBar(ratio: number, width = 8): string {
  const clamped = Math.max(0, Math.min(1, Number(ratio) || 0));
  const filled = Math.round(clamped * width);
  return '▓'.repeat(filled) + '░'.repeat(Math.max(0, width - filled));
}

function buildTableChartElements(headers: string[], rows: string[][]): object[] {
  if (headers.length < 2 || rows.length < 2 || rows.length > 10) return [];
  for (let colIdx = 1; colIdx < headers.length; colIdx++) {
    const headerName = (headers[colIdx] ?? '').replace(/\*\*/g, '').trim();
    if (/^(?:序号|编号|ID|阶段|时间|日期|路径|产物)$/i.test(headerName)) continue;
    const parsedValues = rows.map((r) => {
      const cell = String(r[colIdx] || '')
        .replace(/\*\*/g, '')
        .replace(/`/g, '')
        .replace(/^[🟢🔵🟠🔴✅⚠️❌\s]+/, '')
        .replace(/,/g, '')
        .trim();
      const pctMatch = cell.match(/^(\d+(?:\.\d+)?)\s*%$/);
      if (pctMatch) return { kind: 'pct' as const, value: Number(pctMatch[1]), raw: cell };
      const ratioMatch = cell.match(/^(\d+)\s*\/\s*(\d+)$/);
      if (ratioMatch && Number(ratioMatch[2]) > 0) {
        return {
          kind: 'ratio' as const,
          value: (Number(ratioMatch[1]) / Number(ratioMatch[2])) * 100,
          raw: cell,
        };
      }
      const numMatch = cell.match(/^¥?\s*(\d+(?:\.\d+)?)\s*(?:分|ms|秒|条|个|次|积分|元|万)?$/i);
      if (numMatch) return { kind: 'num' as const, value: Number(numMatch[1]), raw: cell };
      return null;
    });
    if (parsedValues.every((v): v is NonNullable<typeof v> => v !== null)) {
      const maxVal = Math.max(...parsedValues.map((v) => v.value), 1);
      const isPct = parsedValues.every((v) => v.kind === 'pct' || v.kind === 'ratio');
      const denom = isPct ? 100 : maxVal;
      const barLines = rows.map((r, i) => {
        const label = String(r[0] || `#${i + 1}`)
          .replace(/\*\*/g, '')
          .trim()
          .slice(0, 14);
        const v = parsedValues[i]!;
        const bar = renderVisualBar(v.value / denom, 10);
        return `**${label}**　${bar}　**${v.raw}**`;
      });
      return [
        {
          tag: 'column_set',
          flex_mode: 'none',
          background_style: 'grey',
          horizontal_spacing: 'default',
          columns: [
            {
              tag: 'column',
              width: 'weighted',
              weight: 1,
              vertical_align: 'top',
              elements: [
                {
                  tag: 'markdown',
                  content: `📊 **${headerName || '核心指标'} · 可视化对比**\n${barLines.join('\n')}`,
                },
              ],
            },
          ],
        },
      ];
    }
  }
  return [];
}

function tableToCardElements(headers: string[], rows: string[][]): object[] {
  const keepIndices = headers
    .map((h, idx) =>
      /^(?:sha256|哈希|校验码|绝对路径)$/i.test(h.replace(/\*\*/g, '').trim()) ? -1 : idx,
    )
    .filter((idx) => idx !== -1);

  const cleanHeaders = keepIndices.map((i) => headers[i] ?? '');
  const cleanRows = rows.map((r) => keepIndices.map((i) => decorateCellVisuals(r[i])));
  const colCount = cleanHeaders.length;
  const visualChart = buildTableChartElements(cleanHeaders, cleanRows);

  if (colCount >= 2 && colCount <= 4 && cleanRows.length <= 12) {
    const headerColumns = cleanHeaders.map((h) => ({
      tag: 'column',
      width: 'weighted',
      weight: 1,
      vertical_align: 'top',
      elements: [{ tag: 'markdown', content: `**${h || '-'}**` }],
    }));
    const elements: object[] = [
      ...visualChart,
      {
        tag: 'column_set',
        flex_mode: colCount <= 2 ? 'bisect' : 'trisect',
        background_style: 'grey',
        horizontal_spacing: 'default',
        columns: headerColumns,
      },
    ];
    for (const row of cleanRows) {
      const cols = cleanHeaders.map((_, idx) => ({
        tag: 'column',
        width: 'weighted',
        weight: 1,
        vertical_align: 'top',
        elements: [{ tag: 'markdown', content: row[idx] || '-' }],
      }));
      elements.push({
        tag: 'column_set',
        flex_mode: 'none',
        background_style: 'default',
        horizontal_spacing: 'default',
        columns: cols,
      });
    }
    return elements;
  }

  const lines = cleanRows.map((row, idx) => {
    const pairs = cleanHeaders
      .map((h, i) => `**${h || `列${i + 1}`}**：${row[i] || '-'}`)
      .join(' ｜ ');
    return `${idx + 1}. ${pairs}`;
  });
  return [...visualChart, { tag: 'markdown', content: lines.join('\n') }];
}

function extractKpiMetrics(rawText: string): Array<{ label: string; value: string }> {
  const text = normalizeFeishuMarkdown(rawText);
  const kpis: Array<{ label: string; value: string }> = [];
  const seenLabels = new Set<string>();

  const kvRegex =
    /(?:^|\n)\s*(?:[-*•]|\d+[.、])?\s*\*\*([^*\n：:]{2,10})\*\*\s*[:：]\s*([^\n。；|]{1,18})(?=[。；\n|]|$)/g;
  for (const match of text.matchAll(kvRegex)) {
    const label = (match[1] ?? '').trim();
    const val = (match[2] ?? '').replace(/\*\*/g, '').trim();
    if (/^(?:结论|核心结论|总结|背景|说明|原因|详情|下一步|待拍板|产物|文件)/.test(label)) continue;
    if (
      /\d|通过|完成|正常|就绪|达标|异常|失败|在线|已连接|已启用/.test(val) &&
      !seenLabels.has(label)
    ) {
      seenLabels.add(label);
      kpis.push({ label, value: decorateCellVisuals(`**${val}**`) });
    }
    if (kpis.length >= 3) break;
  }

  return kpis.length >= 2 ? kpis.slice(0, 4) : [];
}

function buildKpiElements(kpis: Array<{ label: string; value: string }>): object[] {
  if (!Array.isArray(kpis) || kpis.length < 2) return [];
  return [
    {
      tag: 'column_set',
      flex_mode: kpis.length === 2 ? 'bisect' : 'trisect',
      background_style: 'grey',
      horizontal_spacing: 'default',
      columns: kpis.map((item) => ({
        tag: 'column',
        width: 'weighted',
        weight: 1,
        vertical_align: 'top',
        elements: [
          {
            tag: 'markdown',
            content: `${item.label}\n${item.value}`,
          },
        ],
      })),
    },
  ];
}

function markdownToCardElements(rawText: string): object[] {
  const sanitizedText = IncrementalMarkdownAndJsonRepair.sanitizeMarkdown(rawText);
  const lines = String(sanitizedText || '')
    .replace(/\r\n/g, '\n')
    .split('\n');
  const blocks: object[] = [];
  let textBuf: string[] = [];
  let i = 0;

  const flushText = (): void => {
    const joined = normalizeFeishuMarkdown(textBuf.join('\n'));
    textBuf = [];
    if (!joined) return;
    if (joined.length <= MAX_MARKDOWN_ELEMENT_CHARS) {
      blocks.push({ tag: 'markdown', content: joined });
    } else {
      for (let offset = 0; offset < joined.length; offset += MAX_MARKDOWN_ELEMENT_CHARS) {
        blocks.push({
          tag: 'markdown',
          content: joined.slice(offset, offset + MAX_MARKDOWN_ELEMENT_CHARS),
        });
      }
    }
  };

  while (i < lines.length) {
    const line = lines[i];
    const nextLine = lines[i + 1];
    if (
      line?.trim().startsWith('|') &&
      line?.trim().endsWith('|') &&
      typeof nextLine === 'string' &&
      isTableSeparatorLine(nextLine)
    ) {
      flushText();
      const headers = splitTableRow(line);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i]!.trim().startsWith('|') && lines[i]!.trim().endsWith('|')) {
        if (!isTableSeparatorLine(lines[i]!)) {
          rows.push(splitTableRow(lines[i]!));
        }
        i += 1;
      }
      if (rows.length > 0) {
        blocks.push(...tableToCardElements(headers, rows));
      }
      continue;
    }
    if (line !== undefined) textBuf.push(line);
    i += 1;
  }
  flushText();
  return blocks;
}

function undoButton(options: RunCardRenderOptions): object {
  const value: Record<string, unknown> = { cmd: 'undo' };
  if (options.signCallback) {
    value.__bridge_cb = true;
    value.bridge_token = options.signCallback('undo');
  }
  return {
    tag: 'action',
    actions: [
      {
        tag: 'button',
        text: { tag: 'plain_text', content: '↩️ 一键撤回' },
        type: 'default',
        behaviors: [{ type: 'callback', value }],
      }
    ]
  };
}

function renderRichCard(state: RunState, options: RunCardRenderOptions): object {
  const botName = options.botName || '哈基米2.0';
  const elements: object[] = [];

  const thinkingPanel = buildRichThinkingAndToolsPanel(state);
  if (thinkingPanel) {
    elements.push(thinkingPanel);
  }

  const textPieces: string[] = [];
  for (const b of state.blocks) {
    if (b.kind === 'text' && b.content.trim()) {
      textPieces.push(b.content.trim());
    }
  }
  if (textPieces.length === 0 && state.finalText?.trim()) {
    textPieces.push(state.finalText.trim());
  }
  const fullText = textPieces.join('\n\n');

  if (state.terminal === 'done' && fullText) {
    const kpis = extractKpiMetrics(fullText);
    if (kpis.length >= 2) {
      elements.push(...buildKpiElements(kpis));
    }
  }

  if (fullText) {
    const displayMd = state.terminal === 'running' ? `${fullText} ▍` : fullText;
    elements.push(...markdownToCardElements(displayMd));
  }

  if (state.terminal === 'interrupted') {
    elements.push(noteMd('_⏹ 任务已被手动终止_'));
  } else if (state.terminal === 'idle_timeout') {
    const mins = state.idleTimeoutMinutes ?? 0;
    elements.push(noteMd(`_⏱ ${mins} 分钟无响应，已自动终止_`));
  } else if (state.terminal === 'error' && state.errorMsg) {
    elements.push(noteMd(`⚠️ **执行异常**：${state.errorMsg}`));
    elements.push(reconnectButton(options));
  } else if (state.terminal === 'done' && !fullText) {
    elements.push(noteMd('_（已完成处理）_'));
  }

  if (state.terminal === 'running') {
    if (state.footer) elements.push(footerStatus(state.footer));
    elements.push({ tag: 'action', actions: [stopButton(options)] });
  } else if (state.terminal === 'done') {
    elements.push(undoButton(options));
  }

  let headerTemplate = 'wathet';
  let headerTitle = `🤖 ${botName} · 思考与处理中…`;
  if (
    state.terminal === 'error' ||
    state.terminal === 'interrupted' ||
    state.terminal === 'idle_timeout'
  ) {
    headerTemplate = 'red';
    headerTitle = `⚠️ ${botName} · 执行异常提示`;
  } else if (state.terminal === 'done') {
    headerTemplate = 'turquoise';
    headerTitle = `📊 ${botName} · 执行简报`;
  }

  return deepMaskEmails({
    schema: '2.0',
    config: {
      wide_screen_mode: true,
      update_multi: true,
      streaming_mode: state.terminal === 'running',
      summary: { content: summaryText(state) },
    },
    header: {
      template: headerTemplate,
      title: { tag: 'plain_text', content: headerTitle },
    },
    body: { elements },
  });
}
