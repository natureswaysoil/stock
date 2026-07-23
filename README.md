# Stock ADX backstudy

This repository screens lower-priced US stocks and studies ADX threshold
crossovers using Yahoo Finance data.

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
another path.

## Validate

```powershell
python -m unittest discover -s tests -v
python -m py_compile adx_daily_study.py indicator_backtest.py indicator_comparison.py
```
