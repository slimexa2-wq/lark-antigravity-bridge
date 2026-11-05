export class IncrementalMarkdownAndJsonRepair {
  /**
   * Fixes unclosed markdown elements in a streaming markdown string.
   * Closes unclosed code blocks and unclosed tables.
   */
  static sanitizeMarkdown(text: string): string {
    if (!text) return '';

    const lines = text.split('\n');
    let inCodeBlock = false;
    let codeBlockMarker = '';

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]!;
      const match = line.match(/^(\s*)(`{3,}|~{3,})/);
      if (match) {
        if (!inCodeBlock) {
          inCodeBlock = true;
          codeBlockMarker = match[2]!;
        } else {
          // If we see the same marker, we close it
          if (match[2] === codeBlockMarker) {
            inCodeBlock = false;
          }
        }
      }
    }

    let result = text;

    // Close code block if needed
    if (inCodeBlock) {
      if (!result.endsWith('\n')) {
        result += '\n';
      }
      result += codeBlockMarker;
    }

    // Now handle tables if not in a code block at the end (or even if we closed it)
    // Feishu tables look like:
    // | Header |
    // | --- |
    // | Row
    // We need to make sure the last line is a closed table row if it started with |
    const newLines = result.split('\n');
    const lastLineIdx = newLines.length - 1;
    if (lastLineIdx >= 0) {
      const lastLine = newLines[lastLineIdx]!;
      if (lastLine.trim().startsWith('|') && !lastLine.trim().endsWith('|')) {
        newLines[lastLineIdx] = lastLine + ' |';
        result = newLines.join('\n');
      }
    }

    return result;
  }

  /**
   * Best-effort JSON sanitizer for truncated JSON strings.
   * Very useful when an agent streams JSON.
   */
  static sanitizeJson(jsonStr: string): string {
    let s = jsonStr.trim();
    if (!s) return s;

    // Remove any trailing commas
    s = s.replace(/,\s*$/, '');

    let inString = false;
    let escapeNext = false;
    const stack: string[] = [];

    for (let i = 0; i < s.length; i++) {
      const char = s[i];

      if (escapeNext) {
        escapeNext = false;
        continue;
      }

      if (char === '\\') {
        escapeNext = true;
        continue;
      }

      if (char === '"') {
        inString = !inString;
        continue;
      }

      if (!inString) {
        if (char === '{' || char === '[') {
          stack.push(char);
        } else if (char === '}') {
          if (stack[stack.length - 1] === '{') stack.pop();
        } else if (char === ']') {
          if (stack[stack.length - 1] === '[') stack.pop();
        }
      }
    }

    let result = s;
    if (inString) {
      result += '"';
    }

    // Close remaining structures
    while (stack.length > 0) {
      const char = stack.pop();
      if (char === '{') {
        result += '}';
      } else if (char === '[') {
        result += ']';
      }
    }

    return result;
  }
}
