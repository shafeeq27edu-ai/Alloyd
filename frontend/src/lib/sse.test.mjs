import test from "node:test";
import assert from "node:assert/strict";

import { SSEParser } from "./sse.ts";

test("dispatches an event on a blank line", () => {
  const parser = new SSEParser();
  const events = parser.push("event: routing\ndata: {\"a\":1}\n\n");
  assert.deepEqual(events, [{ event: "routing", data: "{\"a\":2}" }]);
});

test("buffers an event split across chunks", () => {
  const parser = new SSEParser();
  assert.deepEqual(parser.push("event: mess"), []);
  assert.deepEqual(parser.push("age\ndata: hel"), []);
  assert.deepEqual(parser.push("lo\n\n"), [{ event: "message", data: "hello" }]);
});

test("handles CRLF line endings", () => {
  const parser = new SSEParser();
  const events = parser.push("event: message\r\ndata: hi\r\n\r\n");
  assert.deepEqual(events, [{ event: "message", data: "hi" }]);
});

test("joins multi-line data with newlines", () => {
  const parser = new SSEParser();
  const events = parser.push("event: message\ndata: line 1\ndata: line 2\n\n");
  assert.deepEqual(events, [{ event: "message", data: "line 1\nline 2" }]);
});

test("ignores comment lines", () => {
  const parser = new SSEParser();
  const events = parser.push(": keep-alive\nevent: done\ndata: {}\n\n");
  assert.deepEqual(events, [{ event: "done", data: "{}" }]);
});

test("dispatches multiple events from one chunk", () => {
  const parser = new SSEParser();
  const events = parser.push(
    "event: routing\ndata: {}\n\nevent: message\ndata: a\n\nevent: done\ndata: {}\n\n"
  );
  assert.deepEqual(events.map((e) => e.event), ["routing", "message", "done"]);
});

test("finish dispatches a trailing event without blank line", () => {
  const parser = new SSEParser();
  assert.deepEqual(parser.push("event: message\ndata: tail"), []);
  assert.deepEqual(parser.finish(), [{ event: "message", data: "tail" }]);
});

test("defaults to message when no event name is set", () => {
  const parser = new SSEParser();
  assert.deepEqual(parser.push("data: x\n\n"), [{ event: "message", data: "x" }]);
});
