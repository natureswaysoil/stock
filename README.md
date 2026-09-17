# Stock ADX backstudy

This repository screens lower-priced US stocks and studies ADX threshold
crossovers using Yahoo Finance data. Weekly and monthly scans use only fully
completed bars. Return measurements enter at the next trading day's open so
they do not assume execution at the close that generated the signal.

The canonical study uses **monthly chart bars by default**. Daily and weekly
bars remain available as command-line overrides.

## Setup

```powershell
python -m pip install -r requirements.txt
```

## Run

Monthly chart (default):

```powershell
python .\adx_daily_study.py
```

Explicit monthly chart:

```powershell
python .\adx_daily_study.py --timeframe monthly
```

Optional alternatives:

```powershell
python .\adx_daily_study.py --timeframe weekly
python .\adx_daily_study.py --timeframe daily
```

Results are written to `adx_crossover_results.csv` unless `--out` specifies
another path. A header-only CSV is written when no stocks qualify, preventing
an older file from being mistaken for current results. When the scan has
results, the CSV is also emailed to `natureswaysoil@gmail.com` through Resend.
Set these environment variables before running:

```powershell
$env:RESEND_API_KEY = "re_your_api_key"
$env:STOCK_EMAIL_FROM = "Stock Scanner <stocks@your-verified-domain.com>"
```

The API key is sent only in the HTTPS authorization header and is never written
to the CSV or console. Verify the sender domain in Resend before using it. For a
restricted Resend test account, `onboarding@resend.dev` can send only to the
email address associated with that account. When no stocks qualify, no email is
sent.

To verify Resend without running the Yahoo Finance screen:

```powershell
python .\adx_daily_study.py --test-email --out resend_email_test.csv
```

To write the CSV without emailing it:

```powershell
python .\adx_daily_study.py --no-email
```

## Interpretation limitation

The multi-indicator comparison screens today's sub-$2 universe. It is a
retrospective study, not a point-in-time-universe backtest: delisted stocks and
stocks that moved outside today's screen are not represented. Do not treat its
summary return or win rate as an unbiased estimate of future performance.

## Validate

```powershell
python -m unittest discover -s tests -v
python -m py_compile adx_daily_study.py indicator_backtest.py indicator_comparison.py
```
