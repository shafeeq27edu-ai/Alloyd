import test from "node:test";
import assert from "node:assert/strict";

const { formatCost, formatTokens, formatUsage, usageTitle } = await import("./usage.ts");

test("formatTokens adds thousands separators and rejects missing counts", () => {
  assert.equal(formatTokens(0), "0");
  assert.equal(formatTokens(1204), "1,204");
  assert.equal(formatTokens(1234567), "1,234,567");
  assert.equal(formatTokens(null), null);
  assert.equal(formatTokens(undefined), null);
  assert.equal(formatTokens(-1), null);
});

test("formatCost keeps small amounts meaningful", () => {
  assert.equal(formatCost(0.00002), "$0.000020");
  assert.equal(formatCost(0.0123), "$0.0123");
  assert.equal(formatCost(2), "$2.0000");
  assert.equal(formatCost(null), null);
  assert.equal(formatCost(-0.1), null);
});

test("formatUsage marks estimated counts and hides unknown costs", () => {
  assert.equal(
    formatUsage({ input_tokens: 1204, output_tokens: 356, token_source: "provider", estimated_cost_usd: null }),
    "1,204 in · 356 out"
  );
  assert.equal(
    formatUsage({ input_tokens: 1204, output_tokens: 356, token_source: "provider", estimated_cost_usd: 0.0021 }),
    "1,204 in · 356 out · $0.002100"
  );
  assert.equal(
    formatUsage({ input_tokens: 1204, output_tokens: 356, token_source: "estimated", estimated_cost_usd: null }),
    "~1,204 in · 356 out"
  );
});

test("formatUsage omits parts that were not measured", () => {
  assert.equal(
    formatUsage({ input_tokens: 12, output_tokens: null, token_source: "estimated", estimated_cost_usd: null }),
    "~12 in"
  );
  assert.equal(
    formatUsage({ input_tokens: null, output_tokens: null, token_source: "provider", estimated_cost_usd: 1 }),
    null
  );
  assert.equal(formatUsage(null), null);
});

test("usageTitle states whether counts are exact", () => {
  assert.match(usageTitle({ input_tokens: 1, output_tokens: 1, token_source: "estimated", estimated_cost_usd: null }), /Estimated/);
  assert.match(usageTitle({ input_tokens: 1, output_tokens: 1, token_source: "provider", estimated_cost_usd: null }), /reported by the provider/);
});
