"""Ensure saved-response analysis never masks missing samples or reverses contrasts."""
from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tasks/004_event_alignment_pilot"))
import analyze_live as analysis
import live
import pilot
import siliconflow as sf


class LiveAnalysisTests(unittest.TestCase):
    def pin_replay(self, run, cost_sources=()):
        """Create trust anchors only for a temporary, entirely fictional run."""
        if not (run / "manifest.json").exists():
            pilot.write_json(run / "manifest.json", dict(output_sha256={}, code_sha256={}))
        (run / "analysis").mkdir(exist_ok=True)
        frozen = pilot.digest_file(run / "manifest.json")
        (run / "analysis/manifest.json").write_text(pilot.canonical(dict(frozen_manifest_sha256=frozen,
            source_receipts_sha256={p.relative_to(run).as_posix(): pilot.digest_file(p)
                for p in [run / "attempt_starts.jsonl", *sorted((run / "receipts").glob("*.json"))]})), encoding="utf-8")
        (run.parent / "bindings.json").write_text(pilot.canonical(dict(runs={frozen: dict(
            analysis_manifest_sha256=pilot.digest_file(run / "analysis/manifest.json"), fictional_api_sources=list(cost_sources))})), encoding="utf-8")

    def saved_bundle(self, root):
        config = live.runtime_config(json.loads((pilot.TASK / "config.json").read_text(encoding="utf-8")), live.settings())
        item = live.fictional_inputs()[0]
        run, source = root / "run", root / "source"
        run.mkdir(); source.mkdir()
        (run / "prompts").mkdir(); (source / "prompts").mkdir(); (run / "receipts").mkdir()
        row = dict(proposition_id=item["proposition_id"], subject_id=item["subject_id"], human_gt="Supported", author_type="llm", time_metadata_conflict="False")
        for folder in (run, source):
            pilot.write_csv(folder / "cohort_llm.csv", [row])
            pilot.write_csv(folder / "cohort_human.csv", [], fields=list(row))
            pilot.write_jsonl(folder / "inputs.jsonl", [item])
            (folder / "selected_patients.csv").write_text("fictional\n", encoding="utf-8")
            (folder / "excluded_invalid.csv").write_text("fictional\n", encoding="utf-8")
            for name, text in pilot.templates().items():
                (folder / "prompts" / (name + ".md")).write_text(text, encoding="utf-8")
        pilot.write_json(run / "preflight.json", dict(protected_files_sha256={}))
        jobs, starts = [], []
        for a in pilot.ARMS:
            req = pilot.make_request(item, a, config, pilot.templates())
            body = sf.api_body(req)
            seq = len(jobs) + 1
            job = dict(sequence=seq, request=req, api_body=body, api_body_sha256=pilot.fingerprint(body))
            jobs.append(job)
            answer = dict(verdict="Supported", reason="Invented evidence.", checks=[dict(aspect=k, assessment="Invented.", evidence_ids=[1]) for k in pilot.ASPECTS[a]])
            response = dict(model=sf.MODEL, choices=[dict(finish_reason="stop", message=dict(content=pilot.canonical(answer)))],
                usage=dict(prompt_tokens=100, completion_tokens=100, total_tokens=200, completion_tokens_details=dict(reasoning_tokens=0)))
            t = dict(http_status=200, response_json=response, response_body_text=pilot.canonical(response), elapsed_seconds=1,
                ended_utc="2026-09-13T13:00:01+00:00", service_retryable=False)
            normalized = sf.normalize_result(req, item, t, config)
            pilot.write_json(run / "receipts" / f"{seq}.json", dict(sequence=seq, attempt=1, api_body_sha256=job["api_body_sha256"], transport=t, normalized=normalized))
            starts.append(dict(sequence=seq, attempt=1, api_body_sha256=job["api_body_sha256"], request_id=req["request_id"]))
        pilot.write_jsonl(run / "attempt_starts.jsonl", starts)
        self.pin_replay(run)
        return run, source, (jobs, config, {item["proposition_id"]: item})

    def test_collector_replays_raw_response_and_detects_tampered_verdict(self):
        with tempfile.TemporaryDirectory() as d:
            run, source, loaded = self.saved_bundle(Path(d))
            with patch.object(live, "load_jobs", return_value=loaded), patch.object(live, "SOURCE", source), patch.object(analysis, "REPLAY_BINDINGS", run.parent / "bindings.json"):
                self.assertTrue(analysis.collect(run)[4]["complete"])
                p = run / "receipts/1.json"
                value = json.loads(p.read_text())
                value["normalized"]["verdict"] = "Not Supported"
                p.write_text(pilot.canonical(value), encoding="utf-8")
                # A malformed fictional source must fail semantic checks even
                # when it was present when that fixture's hashes were captured.
                self.pin_replay(run)
                with self.assertRaisesRegex(ValueError, "normalization"):
                    analysis.collect(run)

    def test_collector_rejects_regeneration_after_terminal_answer(self):
        with tempfile.TemporaryDirectory() as d:
            run, source, loaded = self.saved_bundle(Path(d))
            value = json.loads((run / "receipts/1.json").read_text())
            value["attempt"] = 2
            pilot.write_json(run / "receipts/1b.json", value)
            starts = pilot.jsonl(run / "attempt_starts.jsonl")
            with (run / "attempt_starts.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(pilot.canonical(dict(starts[0], attempt=2)) + "\n")
            self.pin_replay(run)
            with patch.object(live, "load_jobs", return_value=loaded), patch.object(live, "SOURCE", source), patch.object(analysis, "REPLAY_BINDINGS", run.parent / "bindings.json"):
                with self.assertRaisesRegex(ValueError, "regenerated"):
                    analysis.collect(run)

    def test_audit_append_and_missing_editor_file_do_not_block_replay(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run, source, loaded = self.saved_bundle(root)
            audit, editor = root / "audit.md", root / "editor.json"
            audit.write_text("Original review", encoding="utf-8")
            editor.write_text("{}", encoding="utf-8")
            (run / "preflight.json").write_text(pilot.canonical(dict(protected_files_sha256={p.name: pilot.digest_file(p) for p in (audit, editor)})), encoding="utf-8")
            with patch.object(pilot, "ROOT", root), patch.object(live, "load_jobs", return_value=loaded), patch.object(live, "SOURCE", source), patch.object(analysis, "REPLAY_BINDINGS", root / "bindings.json"):
                before = analysis.collect(run)
                audit.write_text("Original review\nLater independent review", encoding="utf-8")
                editor.unlink()
                after = analysis.collect(run)
            self.assertEqual(before[2], after[2])
            self.assertEqual(before[5], after[5])
            self.assertTrue(after[4]["complete"])
            self.assertFalse(after[4]["protected_files_unchanged"])
            self.assertEqual(set(after[4]["protected_files_changes"]), {audit.name, editor.name})

    def test_frozen_inputs_config_and_inference_code_still_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run, source, loaded = self.saved_bundle(root)
            pilot.write_json(run / "config.json", loaded[1])
            with gzip.open(run / "requests.jsonl.gz", "wt", encoding="utf-8") as f:
                f.write("\n".join(pilot.canonical(j) for j in loaded[0]))
            code = root / "inference.py"
            code.write_text("# fictional frozen code\n", encoding="utf-8")
            frozen_files = ["inputs.jsonl", "cohort_llm.csv", "cohort_human.csv", "config.json", "preflight.json", "requests.jsonl.gz", "prompts/common.md"]
            (run / "manifest.json").write_text(pilot.canonical(dict(output_sha256={n: pilot.digest_file(run / n) for n in frozen_files},
                code_sha256={code.name: pilot.digest_file(code)})), encoding="utf-8")
            self.pin_replay(run)
            with patch.object(pilot, "ROOT", root), patch.object(live, "SOURCE", source), patch.object(analysis, "REPLAY_BINDINGS", root / "bindings.json"):
                self.assertTrue(analysis.collect(run)[4]["complete"])
                for name in frozen_files:
                    with self.subTest(file=name):
                        path = run / name
                        original = path.read_bytes()
                        path.write_bytes(original + b"\n")
                        with self.assertRaisesRegex(ValueError, "Frozen input changed"):
                            analysis.collect(run)
                        path.write_bytes(original)
                code.write_text("# changed inference code\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Inference code/settings changed"):
                    analysis.collect(run)

    def test_receipt_bytes_and_original_manifest_are_pinned(self):
        with tempfile.TemporaryDirectory() as d:
            run, source, loaded = self.saved_bundle(Path(d))
            with patch.object(live, "load_jobs", return_value=loaded), patch.object(live, "SOURCE", source), patch.object(analysis, "REPLAY_BINDINGS", run.parent / "bindings.json"):
                receipt = run / "receipts/1.json"
                original = receipt.read_bytes()
                # Semantically identical JSON still violates the original bytes.
                receipt.write_bytes(original + b"\n")
                with self.assertRaisesRegex(ValueError, "Saved receipt/start/recovery file changed"):
                    analysis.collect(run)
                receipt.write_bytes(original)
                manifest = run / "analysis/manifest.json"
                manifest.write_bytes(manifest.read_bytes() + b"\n")
                with self.assertRaisesRegex(ValueError, "Original analysis manifest changed"):
                    analysis.collect(run)
                manifest.unlink()
                with self.assertRaisesRegex(ValueError, "Original analysis manifest changed or missing"):
                    analysis.collect(run)

    def test_fictional_cost_ignores_future_runs_and_rejects_changed_sources(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            run, _, _ = self.saved_bundle(root)
            sources = []
            for name, value, field in (("run_001/normalized.json", {"cost": {"cny": .01}}, ["cost", "cny"]),
                    ("run_002/summary.json", {"cost_estimate_cny": .16}, ["cost_estimate_cny"])):
                path = root / "api_preflight" / name
                path.parent.mkdir(parents=True)
                pilot.write_json(path, value)
                sources.append(dict(path=path.relative_to(root).as_posix(), sha256=pilot.digest_file(path), cost_field=field))
            self.pin_replay(run, sources)
            with patch.object(pilot, "ROOT", root), patch.object(pilot, "OUT", root), patch.object(analysis, "REPLAY_BINDINGS", root / "bindings.json"):
                before = analysis.fictional_api_cost(run)
                later = root / "api_preflight/run_999"
                later.mkdir()
                pilot.write_json(later / "summary.json", dict(cost_estimate_cny=1))
                pilot.write_json(later / "normalized.json", dict(cost=dict(cny=2)))
                self.assertEqual(before, analysis.fictional_api_cost(run))
                self.assertAlmostEqual(before["estimated_cny"], .17)
                selected = root / sources[1]["path"]
                selected.write_text(pilot.canonical(dict(cost_estimate_cny=1.16)), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Fictional cost source changed or missing"):
                    analysis.fictional_api_cost(run)
                selected.unlink()
                with self.assertRaisesRegex(ValueError, "Fictional cost source changed or missing"):
                    analysis.fictional_api_cost(run)

    def test_unknown_run_cannot_inherit_another_runs_cost_binding(self):
        with tempfile.TemporaryDirectory() as d:
            run, _, _ = self.saved_bundle(Path(d))
            with patch.object(analysis, "REPLAY_BINDINGS", run.parent / "bindings.json"):
                (run / "manifest.json").write_text("{}\n", encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "Unregistered frozen run"):
                    analysis.fictional_api_cost(run)

    def data(self):
        base = json.loads((pilot.TASK / "config.json").read_text(encoding="utf-8"))
        config = live.runtime_config(base, live.settings())
        config["evaluation"]["iterations"] = 10
        cohort, terminal, receipts = [], [], []
        for author in ("llm", "human"):
            for i in range(6):
                pid = f"fictional-{author}-{i}"
                truth = pilot.LABELS[i % 3]
                cohort.append(dict(proposition_id=pid, subject_id=f"fictional-patient-{i}", human_gt=truth,
                    author_type=author, time_metadata_conflict=str(i == 5)))
                for a in pilot.ARMS:
                    u = dict(input_tokens=1000, output_tokens=100, reasoning_tokens=0, cache_hit_tokens=0,
                        reasoning_counter_basis="provider_explicit_counter", cache_counter_available=True, total_tokens=1100)
                    r = dict(request_id=a + ":" + pid, proposition_id=pid, arm=a, status="success",
                        verdict=truth if a == "event_alignment" else "Supported", structural_errors=[], adherence_errors=[],
                        usage=u, cost=sf.cost_estimate(u, "2026-09-13T13:00:00+00:00"), explanation_words=20,
                        model_returned=sf.MODEL, system_fingerprint="", finish_reason="stop")
                    r["output_text"] = pilot.canonical(dict(verdict=r["verdict"], reason="Invented evidence.", checks=[
                        dict(aspect=k, assessment="Invented.", evidence_ids=[1]) for k in pilot.ASPECTS[a]]))
                    terminal.append(r)
                    receipts.append(dict(sequence=len(receipts)+1, attempt=1, normalized=r, budget_charge_cny=r["cost"]["cny"],
                        transport=dict(started_utc="2026-09-13T13:00:00+00:00", ended_utc="2026-09-13T13:00:01+00:00",
                            http_status=200, elapsed_seconds=1, outcome_unknown=False, response_headers={})))
        checks = dict(complete=True, failures=[], expected_requests=36)
        return config, cohort, terminal, receipts, checks, {}

    def test_machine_analysis_is_deterministic_and_uses_full_shared_protocol(self):
        data = self.data()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "manifest.json").write_text("{}", encoding="utf-8")
            with patch.object(analysis, "collect", return_value=data), patch.object(pilot, "OUT", root), patch.object(analysis, "fictional_api_cost", return_value=dict(estimated_cny=0, separate_from_real_inference=True)):
                analysis.analyze(root, root / "a", False)
                analysis.analyze(root, root / "b", False)
            a = root / "a"
            for name in ("metrics.json", "robustness.json", "usage.json", "contrasts.csv", "changed_predictions.csv"):
                self.assertEqual((a / name).read_bytes(), (root / "b" / name).read_bytes())
            m = json.loads((a / "metrics.json").read_text())
            self.assertEqual(m["llm"]["primary"]["metrics"]["event_alignment"]["n"], 6)
            self.assertEqual(m["llm"]["exclude_time_conflicts"]["metrics"]["structured"]["n"], 5)
            self.assertEqual(m["human"]["primary"]["contrasts"]["event_alignment_minus_structured"]["metrics"]["mcc"]["delta"], 1)

    def test_failed_routine_keeps_full_denominator_blocks_its_scores_but_not_complete_primary_pair(self):
        data = list(self.data())
        data[4] = dict(complete=False, failures=[dict(request_id="fictional-failed")])
        data[2][0].update(status="failed", verdict=None, structural_errors=["Truncated"])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "manifest.json").write_text("{}", encoding="utf-8")
            with patch.object(analysis, "collect", return_value=data), patch.object(pilot, "OUT", root), patch.object(analysis, "fictional_api_cost", return_value=dict(estimated_cny=0, separate_from_real_inference=True)):
                analysis.analyze(root, root / "output", False)
            self.assertTrue((root / "output/response_checks.json").exists())
            metrics = json.loads((root / "output/metrics.json").read_text())
            self.assertEqual(metrics["llm"]["primary"]["metrics"]["routine"]["status"], "blocked_incomplete_predictions")
            self.assertEqual(metrics["llm"]["primary"]["metrics"]["routine"]["expected_n"], 6)
            self.assertEqual(metrics["llm"]["primary"]["contrasts"]["event_alignment_minus_structured"]["coverage"]["evaluated_n"], 6)
            self.assertEqual(len(pilot.read_csv(root / "output/predictions_routine.csv")[1]), 12)

    def test_budget_covers_unknown_attempts_and_explicit_missing_counters(self):
        _, cohort, terminal, receipts, _, _ = self.data()
        missing = copy.deepcopy(receipts[0])
        missing["normalized"].pop("usage")
        missing["normalized"].pop("cost")
        missing["transport"]["outcome_unknown"] = True
        missing["budget_charge_cny"] = .1
        summary, _ = analysis.usage_summary([*receipts, missing], terminal, cohort)
        self.assertEqual(summary["extra_service_attempts"], 1)
        self.assertEqual(summary["total"]["unknown_charge_bound_cny"], .1)
        self.assertEqual(summary["total"]["usage_missing_attempts"], 1)

    def test_leave_one_patient_out_direction_and_counts(self):
        _, cohort, terminal, _, _, _ = self.data()
        predictions = {a: [dict(proposition_id=r["proposition_id"], verdict=r["verdict"]) for r in terminal if r["arm"] == a] for a in pilot.ARMS}
        result = analysis.robustness(cohort, predictions)
        self.assertEqual(result["llm"]["positive_patient_nets"], 4)
        self.assertEqual(result["llm"]["negative_patient_nets"], 0)
        self.assertEqual(result["llm"]["lopo_mcc_delta_min"], 1)
        self.assertEqual(result["human"]["lopo_mcc_delta_max"], 1)

    def test_complete_component_path_matches_original_all_arm_evaluator_exactly(self):
        _, cohort, terminal, _, _, _ = self.data()
        predictions = {a: [dict(proposition_id=r["proposition_id"], verdict=r["verdict"]) for r in terminal if r["arm"] == a] for a in pilot.ARMS}
        self.assertEqual(analysis.evaluate_complete_components(cohort, predictions, 10), pilot.evaluate_arms(cohort, predictions, 10))


if __name__ == "__main__":
    unittest.main()
