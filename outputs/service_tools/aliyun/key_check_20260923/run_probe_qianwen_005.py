"""One bounded repeat using the user's latest local key and Qianwen endpoint."""
import run_probe_qianwen_002 as probe

probe.ATTEMPT = probe.BASE / "attempt_005"
probe.EXPECTED_CONFIG_URL = "https://maas.qianwenaiapi.com/compatible-mode/v1"
probe.PRIOR_ALIYUN_URL = ""
probe.PRIOR_RESERVATION_CNY = 0.40
probe.THIS_RESERVATION_CNY = 0.10

if __name__ == "__main__":
    raise SystemExit(probe.main())
