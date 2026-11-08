export interface SSEEvent {
  event: string;
  data: string;
}

/**
 * Incremental SSE parser that is safe across chunk boundaries.
 * Handles CRLF line endings, comments, multi-line data, and dispatch on a blank line.
 */
export class SSEParser {
  private buffer = "";
  private eventName = "";
  private dataLines: string[] = [];

  push(chunk: string): SSEEvent[] {
    this.buffer += chunk;
    const events: SSEEvent[] = [];

    let newline = this.buffer.indexOf("\n");
    while (newline !== -1) {
      let line = this.buffer.slice(0, newline);
      this.buffer = this.buffer.slice(newline + 1);
      if (line.endsWith("\r")) line = line.slice(0, -1);
      this.handleLine(line, events);
      newline = this.buffer.indexOf("\n");
    }

    return events;
  }

  finish(): SSEEvent[] {
    const events: SSEEvent[] = [];
    if (this.buffer.length > 0) {
      let line = this.buffer;
      if (line.endsWith("\r")) line = line.slice(0, -1);
      this.buffer = "";
      this.handleLine(line, events);
    }
    this.dispatch(events);
    return events;
  }

  private handleLine(line: string, events: SSEEvent[]) {
    if (line === "") {
      this.dispatch(events);
      return;
    }
    if (line.startsWith(":")) return;

    const colon = line.indexOf(":");
    const field = colon === -1 ? line : line.slice(0, colon);
    let value = colon === -1 ? "" : line.slice(colon + 1);
    if (value.startsWith(" ")) value = value.slice(1);

    if (field === "event") {
      this.eventName = value;
    } else if (field === "data") {
      this.dataLines.push(value);
    }
  }

  private dispatch(events: SSEEvent[]) {
    if (this.dataLines.length === 0) {
      this.eventName = "";
      return;
    }
    events.push({
      event: this.eventName || "message",
      data: this.dataLines.join("\n"),
    });
    this.eventName = "";
    this.dataLines = [];
  }
}
