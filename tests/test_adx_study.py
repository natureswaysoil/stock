import unittest

import pandas as pd

from adx_daily_study import (
    history_months_for,
    parse_args,
    resample_monthly,
)


class MonthlyTimeframeTests(unittest.TestCase):
    def test_monthly_is_default_timeframe(self):
        self.assertEqual(parse_args([]).timeframe, "monthly")

    def test_timeframe_can_still_be_overridden(self):
        self.assertEqual(parse_args(["--timeframe", "weekly"]).timeframe, "weekly")

    def test_monthly_resample_uses_monthly_ohlc(self):
        source = pd.DataFrame(
            {
                "date": pd.to_datetime(
                    ["2026-01-02", "2026-01-30", "2026-02-02", "2026-02-27"]
                ),
                "high": [11.0, 13.0, 14.0, 12.0],
                "low": [9.0, 8.0, 10.0, 7.0],
                "close": [10.0, 12.0, 13.0, 8.0],
            }
        )

        monthly = resample_monthly(source)

        self.assertEqual(len(monthly), 2)
        self.assertEqual(monthly.loc[0, "high"], 13.0)
        self.assertEqual(monthly.loc[0, "low"], 8.0)
        self.assertEqual(monthly.loc[0, "close"], 12.0)
        self.assertEqual(monthly.loc[1, "high"], 14.0)
        self.assertEqual(monthly.loc[1, "low"], 7.0)
        self.assertEqual(monthly.loc[1, "close"], 8.0)

    def test_monthly_history_includes_adx_warmup(self):
        self.assertGreaterEqual(history_months_for("monthly", 6, 10), 32)


if __name__ == "__main__":
    unittest.main()
