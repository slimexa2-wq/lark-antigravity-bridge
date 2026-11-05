/**
 * Automatically splits super-long text into smaller chunks based on natural
 * boundaries (double newlines, single newlines) to preserve readability and
 * markdown structure. Falls back to raw character slicing if necessary.
 *
 * @param text The input text to chunk.
 * @param maxLength The maximum length of each chunk (default 3000 chars, well within typical Feishu card limits).
 * @returns An array of text chunks.
 */
export function smartChunkText(text: string, maxLength: number = 3000): string[] {
  if (!text) return [];

  const chunks: string[] = [];
  let currentText = text;

  while (currentText.length > 0) {
    if (currentText.length <= maxLength) {
      chunks.push(currentText);
      break;
    }

    // Try to find a good split point within the maxLength window
    const searchWindow = currentText.substring(0, maxLength);

    // 1. Try double newline (paragraph boundary)
    let splitIndex = searchWindow.lastIndexOf('\n\n');
    let offset = 2; // Length of '\n\n'

    // 2. Fallback to single newline
    if (splitIndex === -1) {
      splitIndex = searchWindow.lastIndexOf('\n');
      offset = 1; // Length of '\n'
    }

    // 3. Fallback to space
    if (splitIndex === -1) {
        splitIndex = searchWindow.lastIndexOf(' ');
        offset = 1; // Length of ' '
    }

    // 4. Ultimate fallback: hard split at maxLength
    if (splitIndex === -1 || splitIndex === 0) {
      splitIndex = maxLength;
      offset = 0; // Hard cut, don't skip any characters if we can't find a boundary
    }

    chunks.push(currentText.substring(0, splitIndex));
    currentText = currentText.substring(splitIndex + offset);
  }

  return chunks;
}
