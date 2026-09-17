import crypto from "node:crypto";

function json(response, status, body) {
  response.status(status).setHeader("Content-Type", "application/json");
  response.end(JSON.stringify(body));
}

function equalSecret(received, expected) {
  if (typeof received !== "string" || typeof expected !== "string") return false;
  const left = Buffer.from(received);
  const right = Buffer.from(expected);
  return left.length === right.length && crypto.timingSafeEqual(left, right);
}

function validNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

export default async function handler(request, response) {
  if (request.method !== "POST") return json(response, 405, { error: "method_not_allowed" });

  const expectedSecret = process.env.TRADINGVIEW_WEBHOOK_SECRET;
  const resendKey = process.env.RESEND_API_KEY;
  const sender = process.env.STOCK_EMAIL_FROM;
  const recipient = process.env.STOCK_EMAIL_TO || "natureswaysoil@gmail.com";
  if (!expectedSecret || !resendKey || !sender) {
    return json(response, 503, { error: "server_not_configured" });
  }

  let payload;
  try {
    payload = typeof request.body === "string" ? JSON.parse(request.body) : request.body;
  } catch {
    return json(response, 400, { error: "invalid_json" });
  }
  if (!payload || !equalSecret(payload.secret, expectedSecret)) {
    return json(response, 401, { error: "unauthorized" });
  }

  const ticker = String(payload.ticker || "").toUpperCase();
  const exchange = String(payload.exchange || "").toUpperCase();
  const timeframe = String(payload.timeframe || "");
  const close = validNumber(payload.close);
  const volume = validNumber(payload.volume);
  if (!/^[A-Z0-9._-]{1,20}$/.test(ticker) || close === null || volume === null) {
    return json(response, 400, { error: "invalid_alert" });
  }

  const subject = `ADX stock signal: ${ticker} at $${close.toFixed(3)}`;
  const body = [
    "TradingView detected a completed-bar ADX crossover.",
    "",
    `Ticker: ${ticker}`,
    `Exchange: ${exchange || "Unknown"}`,
    `Timeframe: ${timeframe || "Unknown"}`,
    `Close: $${close.toFixed(3)}`,
    `Volume: ${Math.round(volume).toLocaleString("en-US")}`,
    `Bar time: ${payload.time || "Unknown"}`,
  ].join("\n");

  const idempotencySource = [ticker, exchange, timeframe, payload.time, close, volume].join("|");
  const resendResponse = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${resendKey}`,
      "Content-Type": "application/json",
      "Idempotency-Key": crypto.createHash("sha256").update(idempotencySource).digest("hex"),
    },
    body: JSON.stringify({ from: sender, to: [recipient], subject, text: body }),
  });
  const result = await resendResponse.json();
  if (!resendResponse.ok || !result.id) {
    console.error("Resend rejected TradingView alert", resendResponse.status, result);
    return json(response, 502, { error: "email_failed" });
  }

  return json(response, 200, { ok: true, email_id: result.id });
}
