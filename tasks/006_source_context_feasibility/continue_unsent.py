"""Registered continuation: skip a frozen unknown outcome, send only pending work.

Does not retry the unknown request, release its reservation, or change raw receipts.
The original request manifest, adapter and 8 CNY authorization remain binding.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import context_feasibility as cf
import run_context_pilot as original
from verifact_research.inference.siliconflow_pool import file_hash, load_accounts, require, save


class ContinueUnsentRunner(original.MeteredRunner):
    def __init__(self, *args, terminal_unknown, **kwargs):
        super().__init__(*args, **kwargs)
        self.terminal_unknown = terminal_unknown

    def _initialize(self):
        super()._initialize()
        unknown = {k for k, v in self.state["jobs"].items() if v["status"] == "unknown"}
        require(unknown == set(self.terminal_unknown), "Unregistered unknown outcome; stop")
        for request_id, expected in self.terminal_unknown.items():
            require(self.state["jobs"][request_id] == expected, "Frozen failed request changed")
        if self.halt == "unknown_previous_outcome":
            self.halt = None

    def _one(self, index, job):
        if job["request_id"] in self.terminal_unknown:
            return
        super()._one(index, job)


def main(prep, run, authorization, registration, workers=4):
    jobs = original.load_preparation(prep)
    approval = json.loads(authorization.read_text(encoding="utf-8"))
    require(approval.get("approved") is True and approval.get("budget_cny") == 8
        and approval.get("logical_requests") == len(jobs)
        and approval.get("preparation_manifest_sha256") == file_hash(prep / "manifest.json")
        and approval.get("adapter_sha256") == file_hash(Path(original.__file__)), "Approval differs")
    require(run.resolve().parent == cf.OUT.resolve() and run.name.startswith("run_"), "Wrong run location")
    require(not (run / "runner.lock").exists(), "An execution lock exists")
    state = json.loads((run / "state.json").read_text(encoding="utf-8"))
    if not registration.exists():
        unknown = {k: v for k, v in state["jobs"].items() if v["status"] == "unknown"}
        require(unknown and all(v["receipts"] for v in unknown.values()), "Expected receipted unknown outcome")
        require(all(v["status"] in {"unknown", "response_received"} or
            (v["status"] == "pending" and v["attempts"] == 0) for v in state["jobs"].values()),
            "Continuation must initially contain only frozen failures, received answers and unsent jobs")
        save(registration, dict(created_utc=datetime.now(timezone.utc).isoformat(),
            handling="Post-pause execution amendment: keep unknown outcomes as terminal failures; continue unsent original jobs only; no unknown retry or refund",
            original_state=state, original_state_sha256=file_hash(run / "state.json"),
            authorization_sha256=file_hash(authorization), preparation_manifest_sha256=file_hash(prep / "manifest.json"),
            run_manifest_sha256=file_hash(run / "manifest.json"), continuation_sha256=file_hash(Path(__file__)),
            terminal_unknown=unknown), new=True)
    registered = json.loads(registration.read_text(encoding="utf-8"))
    require(registered["continuation_sha256"] == file_hash(Path(__file__)), "Continuation code changed")
    for name, path in (("authorization_sha256", authorization), ("preparation_manifest_sha256", prep / "manifest.json"),
            ("run_manifest_sha256", run / "manifest.json")):
        require(registered[name] == file_hash(path), "Registered inputs changed")
    accounts = load_accounts(cf.ROOT / ".env.siliconflow_pool")
    prior_completed = -1
    while True:
        runner = ContinueUnsentRunner(accounts, jobs, run, 8, file_hash(prep / "manifest.json"),
            terminal_unknown=registered["terminal_unknown"])
        result = runner.run(workers)
        unresolved = {k: v["status"] for k, v in runner.state["jobs"].items()
            if v["status"] != "response_received" and k not in registered["terminal_unknown"]}
        if not unresolved:
            result.update(status="completed_with_frozen_transport_failure", pause_reason=None)
            break
        if result["pause_reason"] != "budget_reservation_limit" or result["completed"] <= prior_completed:
            break
        prior_completed = result["completed"]
    result.update(frozen_unknown_request_ids=sorted(registered["terminal_unknown"]),
        remaining_other_jobs=unresolved, cost_meaning="Public-price usage estimates plus unknown reservations; not invoice",
        execution_amendment_sha256=file_hash(registration))
    save(run / "continuation_summary.json", result)
    print(cf.pilot.canonical(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("preparation", "run", "authorization", "registration"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    main(args.preparation.resolve(), args.run.resolve(), args.authorization.resolve(), args.registration.resolve(), args.workers)
