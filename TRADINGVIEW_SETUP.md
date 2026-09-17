# TradingView ADX scanner setup

## 1. Deploy the webhook

Deploy this repository to Vercel and configure these Production environment variables:

- `RESEND_API_KEY`: the Resend API key
- `STOCK_EMAIL_FROM`: `Stock Scanner <stocks@natureswaysoil.com>`
- `STOCK_EMAIL_TO`: `natureswaysoil@gmail.com`
- `TRADINGVIEW_WEBHOOK_SECRET`: a new random value used only for TradingView alerts

Do not reuse the Resend key as the TradingView secret.

The webhook URL will be:

```text
https://YOUR-VERCEL-DOMAIN/api/tradingview
```

## 2. Add the Pine indicator

1. Open TradingView's Pine Editor.
2. Paste `tradingview/adx_pine_screener.pine`.
3. Save it and add it to Favorites.
4. Open Pine Screener and select the U.S. stock watchlist or index to scan.
5. Select this indicator and choose the `1M` timeframe.
6. Filter `Qualified Signal` equal to `1`.

The signal requires a completed bar, price above $0.10 and below $2.00,
volume above 300,000, ADX crossing above 20, and +DI above -DI.

## 3. Configure the alert

Enable two-factor authentication in TradingView, then create the appropriate
indicator/watchlist alert for `Qualified ADX cross`. Select "Once Per Bar Close".

Set the webhook URL to the deployed `/api/tradingview` URL. Paste this JSON into
the alert message, replacing `YOUR_SCOPED_SECRET` with the exact value stored in
`TRADINGVIEW_WEBHOOK_SECRET`:

```json
{
  "secret": "YOUR_SCOPED_SECRET",
  "ticker": "{{ticker}}",
  "exchange": "{{exchange}}",
  "timeframe": "{{interval}}",
  "close": {{close}},
  "volume": {{volume}},
  "time": "{{time}}",
  "signal": "adx_cross_up"
}
```

Never place the Resend API key in TradingView. The scoped webhook secret can
authorize only this endpoint and should be rotated if exposed.
