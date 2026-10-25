"""One bounded probe of the current Alibaba workspace endpoint, no retries."""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tasks/024_lambda2_transfer_validation"))

from transport_direct024 import DirectClient  # noqa: E402
from verifact_research.inference.aliyun import call_once, load_config  # noqa: E402

config = load_config(ROOT / ".env.aliyun")
assert config.base_url == "https://ws-czxuc8anhqs8o4lk.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
body = json.loads((BASE / "body.json").read_text(encoding="utf-8"))
result = call_once(config, body, BASE / "attempt_006", max_cost_cny=0.10,
                   task_used_cny=0.50, task_cap_cny=10, client=DirectClient(config, timeout=30))
print(json.dumps({k: result[k] for k in ("http_status", "response_received", "response_model",
                                      "usage", "outcome_unknown", "retries")}, ensure_ascii=False))
