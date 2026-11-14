export type MessageUsage = {
  input_tokens: number | null;
  output_tokens: number | null;
  token_source: string | null;
  estimated_cost_usd: number | null;
};

export function formatTokens(count: number | null | undefined): string | null {
  if (count === null || count === undefined || !Number.isFinite(count) || count < 0) {
    return null;
  }
  return count.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

export function formatCost(usd: number | null | undefined): string | null {
  if (usd === null || usd === undefined || !Number.isFinite(usd) || usd < 0) {
    return null;
  }
  // Small spend needs more decimals to stay meaningful.
  return `$${usd.toFixed(usd > 0 && usd < 0.01 ? 6 : 4)}`;
}

/**
 * Renders per-message usage for the assistant metadata row. Returns null when
 * there is nothing honest to show, so the row never displays placeholders.
 * Tokens are prefixed with `~` when the provider did not report exact counts.
 */
export function formatUsage(usage: MessageUsage | null | undefined): string | null {
  if (!usage) return null;
  const input = formatTokens(usage.input_tokens);
  const output = formatTokens(usage.output_tokens);
  if (input === null && output === null) return null;

  const parts = [
    input !== null ? `${input} in` : null,
    output !== null ? `${output} out` : null,
  ].filter((part): part is string => part !== null);
  const tokens = usage.token_source === "estimated" ? `~${parts.join(" · ")}` : parts.join(" · ");
  const cost = formatCost(usage.estimated_cost_usd);
  return cost ? `${tokens} · ${cost}` : tokens;
}

export function usageTitle(usage: MessageUsage | null | undefined): string {
  if (usage?.token_source === "estimated") {
    return "Estimated tokens (the provider did not report exact counts)";
  }
  return "Tokens reported by the provider";
}
