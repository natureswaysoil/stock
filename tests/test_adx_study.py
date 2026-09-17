import base64
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import pandas as pd

from adx_daily_study import (
    history_months_for,
    main,
    parse_args,
    resample_monthly,
    resample_weekly,
    send_results_email,
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

        monthly = resample_monthly(source, as_of="2026-03-15")

        self.assertEqual(len(monthly), 2)
        self.assertEqual(monthly.loc[0, "high"], 13.0)
        self.assertEqual(monthly.loc[0, "low"], 8.0)
        self.assertEqual(monthly.loc[0, "close"], 12.0)
        self.assertEqual(monthly.loc[1, "high"], 14.0)
        self.assertEqual(monthly.loc[1, "low"], 7.0)
        self.assertEqual(monthly.loc[1, "close"], 8.0)

    def test_monthly_resample_excludes_incomplete_month(self):
        source = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-01-30", "2026-02-10"]),
                "high": [11.0, 20.0], "low": [8.0, 7.0], "close": [10.0, 19.0],
            }
        )
        monthly = resample_monthly(source, as_of="2026-02-15")
        self.assertEqual(monthly["date"].dt.strftime("%Y-%m-%d").tolist(), ["2026-01-31"])

    def test_weekly_resample_excludes_incomplete_week(self):
        source = pd.DataFrame(
            {
                "date": pd.to_datetime(["2026-02-06", "2026-02-09"]),
                "high": [11.0, 20.0], "low": [8.0, 7.0], "close": [10.0, 19.0],
            }
        )
        weekly = resample_weekly(source, as_of="2026-02-10")
        self.assertEqual(weekly["date"].dt.strftime("%Y-%m-%d").tolist(), ["2026-02-06"])

    def test_invalid_arguments_are_rejected(self):
        with self.assertRaises(SystemExit):
            parse_args(["--adx-period", "0"])
        with self.assertRaises(SystemExit):
            parse_args(["--price-min", "2", "--price-max", "1"])

    def test_monthly_history_includes_adx_warmup(self):
        self.assertGreaterEqual(history_months_for("monthly", 6, 10), 32)

    @patch("adx_daily_study.urllib.request.urlopen")
    def test_empty_results_send_nothing(self, urlopen):
        sent = send_results_email(
            "missing.csv",
            "natureswaysoil@gmail.com",
            "Stock Scanner <stocks@example.com>",
            "re_test",
            "monthly",
            0,
        )

        self.assertFalse(sent)
        urlopen.assert_not_called()

    @patch("adx_daily_study.urllib.request.urlopen")
    def test_nonempty_results_use_resend(self, urlopen):
        response = urlopen.return_value.__enter__.return_value
        response.read.return_value = b'{"id":"email_123"}'
        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "results.csv"
            csv_path.write_text("ticker,timeframe\nTEST,monthly\n", encoding="utf-8")

            sent = send_results_email(
                csv_path,
                "natureswaysoil@gmail.com",
                "Stock Scanner <stocks@example.com>",
                "re_secret_test_key",
                "monthly",
                1,
            )

        self.assertTrue(sent)
        request = urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(request.full_url, "https://api.resend.com/emails")
        self.assertEqual(payload["to"], ["natureswaysoil@gmail.com"])
        self.assertEqual(payload["subject"], "Stock ADX results: 1 monthly-chart match(es)")
        self.assertEqual(base64.b64decode(payload["attachments"][0]["content"]),
                         b"ticker,timeframe\nTEST,monthly\n")
        self.assertEqual(request.headers["Authorization"], "Bearer re_secret_test_key")

    def test_resend_requires_configuration(self):
        with TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "results.csv"
            csv_path.write_text("ticker\nTEST\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "RESEND_API_KEY"):
                send_results_email(csv_path, "to@example.com", "from@example.com", None, "daily", 1)

    @patch("adx_daily_study.send_results_email")
    def test_email_mode_skips_screener_and_sends_csv(self, send):
        with TemporaryDirectory() as temp_dir, patch.dict(
            "os.environ", {"RESEND_API_KEY": "re_test"}
        ):
            output = Path(temp_dir) / "verification.csv"
            status = main([
                "--test-email", "--out", str(output),
                "--email-from", "Stock Scanner <stocks@example.com>",
            ])
            self.assertEqual(status, 0)
            self.assertTrue(output.is_file())
            send.assert_called_once()


if __name__ == "__main__":
    unittest.main()
