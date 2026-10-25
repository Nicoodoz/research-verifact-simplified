"""Repeat the bounded check using the current, correctly paired local config."""
import run_probe_qianwen_002 as probe

probe.ATTEMPT = probe.BASE / "attempt_003"
probe.EXPECTED_CONFIG_URL = "https://maas.qianwenaiapi.com/compatible-mode/v1"
probe.PRIOR_ALIYUN_URL = ""
probe.PRIOR_RESERVATION_CNY = 0.20
probe.THIS_RESERVATION_CNY = 0.10

if __name__ == "__main__":
    raise SystemExit(probe.main())
