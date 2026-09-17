import assert from "node:assert/strict";
import test from "node:test";
import handler from "../api/tradingview.js";

function responseRecorder() {
  return {
    statusCode: 200,
    headers: {},
    status(code) { this.statusCode = code; return this; },
    setHeader(name, value) { this.headers[name] = value; },
    end(value) { this.body = JSON.parse(value); },
  };
}

test("rejects requests without the webhook secret", async () => {
  process.env.TRADINGVIEW_WEBHOOK_SECRET = "correct-secret";
  process.env.RESEND_API_KEY = "re_test";
  process.env.STOCK_EMAIL_FROM = "Stock Scanner <stocks@example.com>";
  const response = responseRecorder();
  await handler({ method: "POST", body: { secret: "wrong" } }, response);
  assert.equal(response.statusCode, 401);
  assert.deepEqual(response.body, { error: "unauthorized" });
});

test("emails a validated TradingView alert", async () => {
  process.env.TRADINGVIEW_WEBHOOK_SECRET = "correct-secret";
  process.env.RESEND_API_KEY = "re_test";
  process.env.STOCK_EMAIL_FROM = "Stock Scanner <stocks@example.com>";
  const originalFetch = global.fetch;
  global.fetch = async (_url, options) => ({
    ok: true,
    status: 200,
    json: async () => ({ id: "email_123" }),
    options,
  });
  try {
    const response = responseRecorder();
    await handler({
      method: "POST",
      body: {
        secret: "correct-secret", ticker: "ABCD", exchange: "NASDAQ",
        timeframe: "1M", close: 1.25, volume: 500000, time: "2026-09-30T00:00:00Z",
      },
    }, response);
    assert.equal(response.statusCode, 200);
    assert.equal(response.body.email_id, "email_123");
  } finally {
    global.fetch = originalFetch;
  }
});
