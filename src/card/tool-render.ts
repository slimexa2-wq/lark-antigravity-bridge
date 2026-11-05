import type { ToolEntry } from './run-state';

const HEADER_SUMMARY_MAX = 80;
const BODY_FIELD_MAX = 600;
const OUTPUT_MAX = 1200;
/**
 * Cumulative cap on a tool's full body markdown (input + output + code fences
 * + headers). Even with per-field caps, pathological tools (many input
 * fields + maxed-out output) can stack to multi-KB bodies which, multiplied
 * across panels, push the card past Feishu's per-element size limit. This
 * is the last belt across the whole rendered body string.
 */
const BODY_TOTAL_MAX = 2500;

export function toolHeaderText(tool: ToolEntry): string {
  const icon = tool.status === 'done' ? '✅' : tool.status === 'error' ? '❌' : '⏳';
  const summary = summarizeInput(tool.name, tool.input);
  return summary ? `${icon} **${tool.name}** — ${summary}` : `${icon} **${tool.name}**`;
}

export function toolBodyMd(tool: ToolEntry): string {
  const parts: string[] = [];
  const inputMd = renderInput(tool);
  if (inputMd) parts.push(inputMd);

  if (tool.output) {
    const truncated = truncate(tool.output, OUTPUT_MAX);
    if (tool.status === 'error') {
      parts.push(`**Error**\n\`\`\`\n${truncated}\n\`\`\``);
    } else if (tool.name === 'Bash') {
      parts.push(renderBashOutput(truncated));
    } else {
      parts.push(`**Output**\n\`\`\`\n${truncated}\n\`\`\``);
    }
  } else if (tool.status === 'running') {
    parts.push('_运行中…_');
  }

  const body = parts.join('\n\n');
  if (body.length <= BODY_TOTAL_MAX) return body;
  return `${body.slice(0, BODY_TOTAL_MAX)}…\n\n_（body 已截断,完整内容查 \`/doctor\` 或日志）_`;
}

function summarizeInput(name: string, input: unknown): string {
  if (!input || typeof input !== 'object') return '';
  const rec = input as Record<string, unknown>;
  const pick = (key: string, max = HEADER_SUMMARY_MAX): string => {
    const v = rec[key];
    if (typeof v !== 'string') return '';
    let unpacked = v.trim();
    if (unpacked.length >= 2 && unpacked.startsWith('"') && unpacked.endsWith('"')) {
      try {
        const parsed = JSON.parse(unpacked);
        if (typeof parsed === 'string') unpacked = parsed;
      } catch {
        unpacked = unpacked.slice(1, -1);
      }
    }
    const oneLine = unpacked.replace(/\s+/g, ' ').trim();
    return oneLine.length > max ? `${oneLine.slice(0, max)}…` : oneLine;
  };
  switch (name) {
    case 'call_mcp_tool': {
      const server = pick('ServerName', 30);
      const tool = pick('ToolName', 40);
      return server && tool ? `${server} · ${tool}` : tool || server;
    }
    case 'Bash':
      return pick('command');
    case 'run_command':
    case 'command_execution': {
      const summary = pick('toolSummary', 40);
      const cmd = pick('CommandLine') || pick('command');
      return summary && cmd ? `${summary} (${cmd})` : summary || cmd;
    }
    case 'Read':
    case 'Edit':
    case 'Write':
    case 'NotebookEdit':
      return shortenPath(pick('file_path'));
    case 'view_file':
    case 'read_file':
    case 'replace_file_content':
    case 'multi_replace_file_content':
    case 'edit_file':
    case 'write_to_file':
    case 'write_file':
    case 'list_dir':
      return shortenPath(
        pick('file_path') ||
          pick('Path') ||
          pick('AbsolutePath') ||
          pick('TargetFile') ||
          pick('DirectoryPath'),
      );
    case 'Grep':
    case 'grep_search': {
      const pat = pick('pattern', 40) || pick('Query', 40);
      const path = pick('path', 30) || pick('SearchPath', 30);
      return path ? `${pat} in ${shortenPath(path)}` : pat;
    }
    case 'Glob':
    case 'find_by_name':
      return pick('pattern') || pick('Pattern');
    case 'WebFetch':
    case 'read_url_content':
      return pick('url') || pick('Url');
    case 'WebSearch':
    case 'search_web':
      return pick('query', 60);
    case 'Agent':
    case 'Task':
    case 'invoke_subagent':
      return pick('description') || pick('Role') || pick('subagent_type') || pick('TypeName');
    default:
      return (
        pick('toolSummary') ||
        pick('command') ||
        pick('CommandLine') ||
        pick('file_path') ||
        pick('Path') ||
        pick('AbsolutePath') ||
        pick('TargetFile') ||
        pick('path') ||
        pick('query') ||
        pick('Query')
      );
  }
}

function renderInput(tool: ToolEntry): string {
  const input = tool.input;
  if (!input || typeof input !== 'object') return '';
  const rec = input as Record<string, unknown>;
  const str = (k: string): string => (typeof rec[k] === 'string' ? rec[k] as string : '');

  switch (tool.name) {
    case 'Bash':
    case 'run_command':
    case 'command_execution': {
      const cmd = str('command') || str('CommandLine');
      return cmd ? `**Command**\n\`\`\`bash\n${truncate(cmd, BODY_FIELD_MAX)}\n\`\`\`` : '';
    }
    case 'Read':
    case 'Edit':
    case 'Write':
    case 'NotebookEdit':
    case 'view_file':
    case 'read_file':
    case 'replace_file_content':
    case 'multi_replace_file_content':
    case 'edit_file':
    case 'write_to_file':
    case 'write_file':
    case 'list_dir': {
      const fp =
        str('file_path') ||
        str('Path') ||
        str('AbsolutePath') ||
        str('TargetFile') ||
        str('DirectoryPath');
      return fp ? `**File** \`${fp}\`` : '';
    }
    case 'Grep':
    case 'grep_search': {
      const lines: string[] = [];
      const pat = str('pattern') || str('Query');
      const p = str('path') || str('SearchPath');
      if (pat) lines.push(`**Pattern** \`${pat}\``);
      if (p) lines.push(`**Path** \`${p}\``);
      return lines.join('\n');
    }
    case 'WebFetch':
    case 'read_url_content': {
      const u = str('url') || str('Url');
      return u ? `**URL** ${u}` : '';
    }
    case 'WebSearch':
    case 'search_web': {
      const q = str('query') || str('Query');
      return q ? `**Query** \`${truncate(q, BODY_FIELD_MAX)}\`` : '';
    }
    default:
      return '';
  }
}

function renderBashOutput(out: string): string {
  // Some agents wrap stdout/stderr in xml-like tags; keep simple and just dump.
  return `**Output**\n\`\`\`\n${out}\n\`\`\``;
}

function shortenPath(p: string): string {
  return p;
}

function truncate(s: string, max: number): string {
  return s.length > max ? `${s.slice(0, max)}…` : s;
}
