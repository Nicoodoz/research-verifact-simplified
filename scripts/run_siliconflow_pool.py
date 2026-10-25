"""Check local keys or execute a new task under the API budget policy in AGENTS.md."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from verifact_research.inference.siliconflow_pool import Runner, canonical, load_accounts, require


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keys-file", type=Path, default=ROOT / ".env.siliconflow_pool")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check-keys", help="Local format/count check only; no network request")
    run = commands.add_parser("run", help="Paid requests: task estimate <= CNY 40 needs no reconfirmation; otherwise obtain approval (AGENTS.md)")
    run.add_argument("--requests", type=Path, required=True)
    run.add_argument("--output", type=Path, required=True)
    run.add_argument("--budget-cny", type=float, required=True)
    run.add_argument("--max-attempts", type=int, default=5)
    run.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()
    accounts = load_accounts(args.keys_file)
    if args.command == "check-keys":
        print(canonical(dict(configured_accounts=[a.alias for a in accounts], count=len(accounts),
            network_called=False, credentials_validated_online=False)))
        return
    output = args.output.resolve()
    require(output.is_relative_to(ROOT / "outputs") and not output.is_relative_to(ROOT / "outputs/004_event_alignment_pilot"),
        "Use a new output location under outputs/, outside historical 004")
    jobs = [json.loads(line) for line in args.requests.read_text(encoding="utf-8").splitlines() if line.strip()]
    print(canonical(Runner(accounts, jobs, output, args.budget_cny, args.max_attempts).run(args.workers)))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, KeyError, TypeError):
        # Do not leak arbitrary input lines, credentials or raw exception text.
        print("Stopped: check local configuration, output state and the runner documentation. No credentials displayed.", file=sys.stderr)
        sys.exit(1)
