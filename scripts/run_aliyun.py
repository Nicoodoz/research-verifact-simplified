"""Local Alibaba configuration check or one explicitly budgeted request."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from verifact_research.inference.aliyun import load_config, call_once
from verifact_research.inference.siliconflow_pool import canonical, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'.env.aliyun')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('check-config', help='Local only: no API call, no key printed')
    call = sub.add_parser('call', help='One paid request; no retries or experiment continuation')
    call.add_argument('--request', type=Path, required=True, help='Raw OpenAI-compatible JSON body')
    call.add_argument('--output', type=Path, required=True, help='New folder under outputs/service_tools/aliyun')
    call.add_argument('--max-cost-cny', type=float, required=True, help='Price/token based upper reservation for this attempt')
    call.add_argument('--task-used-cny', type=float, required=True, help='Existing total including all suppliers and unknown reservations')
    call.add_argument('--task-cap-cny', type=float, default=40)
    args = parser.parse_args()
    config = load_config(args.config)
    if args.command == 'check-config':
        print(canonical(dict(key_configured=bool(config.api_key), base_url=config.base_url, model=config.model,
                             network_called=False, credentials_validated_online=False)))
        return
    output = args.output.resolve()
    require(output.is_relative_to(ROOT/'outputs/service_tools/aliyun'), 'Use a new service_tools/aliyun output directory')
    body = json.loads(args.request.read_text(encoding='utf-8-sig'))
    result = call_once(config, body, output, max_cost_cny=args.max_cost_cny, task_used_cny=args.task_used_cny, task_cap_cny=args.task_cap_cny)
    # Raw provider text and model outputs stay in receipts; the terminal only shows execution status.
    print(canonical({k: result[k] for k in ('http_status', 'response_received', 'cumulative_reserved_cny', 'outcome_unknown', 'retries')}))
    return 0 if result['response_received'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main() or 0)
    except (ValueError, OSError, KeyError, TypeError):
        print('Stopped: check the local configuration, budget and output directory. No credentials displayed.', file=sys.stderr)
        sys.exit(1)
