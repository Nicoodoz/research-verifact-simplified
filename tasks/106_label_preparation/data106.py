"""Local-only 106 training-pool index and exactly quota-matched label datasets.

Never prints clinical text, sends network requests, imports torch, or opens the
confirmation-patient corpus. Teacher errors and lexical neighbors are selection
proxies, never new clinical labels or certified semantic relation annotations.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import statistics
import sys

import duckdb
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/106_label_preparation"
PRIVATE = ROOT / ".local_models/106_label_preparation"
LABELS = ("Supported", "Not Supported", "Not Addressed")
QUOTAS = dict(zip(LABELS, (320, 96, 96)))
SEED = "106/boundary_cover/v1/"
sys.path.insert(0, str(ROOT / "tasks/104_supervision_evidence"))
from training104 import messages
sys.path.insert(0, str(ROOT / "tasks/105_brief_supervision"))
from tokenizer_cpu105 import CPUPinnedTokenizer


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def rows(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def put(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8"))


def putl(path, values):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes("".join(json.dumps(v, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n" for v in values).encode("utf-8"))


def stats(values):
    a = np.asarray(values, dtype=float)
    return dict(N=len(a), sum=float(a.sum()), mean=float(a.mean()), median=float(np.median(a)),
                min=float(a.min()), p95=float(np.quantile(a, .95)), max=float(a.max()))


def distribution(values):
    values = list(values)
    if not values:
        return dict(N=0)
    return dict(N=len(values), GT=dict(Counter(r["GT"] for r in values)),
                author=dict(Counter(r["author"] for r in values)),
                patients=len({r["sid"] for r in values}),
                paper_r1_supported_on_nonS=sum(r["GT"] != LABELS[0] and r["paper_r1"] == LABELS[0] for r in values),
                paper_r1_NS_NA_swap=sum(r["GT"] in LABELS[1:] and r["paper_r1"] in LABELS[1:] and r["paper_r1"] != r["GT"] for r in values),
                input_tokens=stats([r["input_tokens"] for r in values]),
                claim_tokens=stats([r["claim_tokens"] for r in values]),
                same_reference_teacher_S_fraction_mean=float(np.mean([r["teacher_S_fraction"] for r in values])),
                difficulty_by_GT={g:dict(N=sum(r["GT"]==g for r in values),
                    paper_r1_S=sum(r["GT"]==g and r["paper_r1"]==LABELS[0] for r in values),
                    paper_r1_NS_NA_swap=sum(r["GT"]==g and g in LABELS[1:] and r["paper_r1"] in LABELS[1:] and r["paper_r1"]!=g for r in values),
                    teachers_NS_NA_mixed=sum(r["GT"]==g and r["teacher_NS_NA_mixed"] for r in values)) for g in LABELS},
                existing104_issue_tags=dict(Counter(tag for r in values for tag in r["issue_tags104"])),
                semantic104_status=dict(Counter(r["semantic104_status"] for r in values)))


def source_pool():
    roles = read(ROOT / "outputs/103_lora_selection/patient_roles.json")["patients"]
    allowed = set(map(str, roles["train"]))
    excluded = set(map(str, roles["selection"] + roles["confirmation"]))
    assert len(allowed) == 40 and not allowed & excluded
    # This previously frozen eligible file has only training+selection patients.
    # Discard selection rows immediately; never open 092's all-patient inputs.
    pool = []
    with (ROOT / ".local_models/103_lora_selection/eligible.jsonl").open(encoding="utf-8-sig") as handle:
        for line in handle:
            if line.strip():
                r = json.loads(line)
                if r["role"] == "train":
                    assert str(r["sid"]) in allowed and str(r["sid"]) not in excluded
                    pool.append(r)
    assert len({r["id"] for r in pool}) == len(pool)
    assert {str(r["sid"]) for r in pool} == allowed
    assert all(r["GT"] in LABELS and digest(r["reference"]) == r["reference_id"] for r in pool)
    raw = ROOT / "data/00_raw/verifact-bhc/1.1.0"
    with duckdb.connect() as db:
        db.execute("CREATE TEMP TABLE wanted(id VARCHAR,reference_id VARCHAR)")
        db.executemany("INSERT INTO wanted VALUES (?,?)", [(r["id"], r["reference_id"]) for r in pool])
        truth = dict(db.execute("SELECT p.proposition_id,p.human_gt FROM read_csv_auto(?,all_varchar=true) p JOIN wanted w ON p.proposition_id=w.id", [str(raw / "propositions/human_verdicts.csv.gz")]).fetchall())
        props = {r[0]:r[1:] for r in db.execute("SELECT p.proposition_id,p.text,p.subject_id,p.author_type,p.proposition_type FROM read_csv_auto(?,all_varchar=true) p JOIN wanted w ON p.proposition_id=w.id", [str(raw / "propositions/propositions.csv.gz")]).fetchall()}
        refs = dict(db.execute("SELECT p.reference_id,p.reference FROM read_parquet(?) p JOIN (SELECT DISTINCT reference_id FROM wanted) w USING(reference_id)", [str(raw / "verifact/reference_payloads.parquet")]).fetchall())
        teachers = db.execute("SELECT p.proposition_id,p.rater_alias,p.model,p.verdict,p.reference_id FROM read_parquet(?) p JOIN wanted w ON p.proposition_id=w.id AND p.reference_id=w.reference_id", [str(raw / "verifact/verdicts.parquet")]).fetchall()
    for r in pool:
        text, sid, author, granularity = props[r["id"]]
        assert r["GT"] == truth[r["id"]] and r["claim"] == text and r["sid"] == str(sid) and r["author"] == author
        assert r["reference"] == refs[r["reference_id"]]
        r["proposition_type"] = granularity
    return pool, roles, teachers


def neighbor_index(pool, excluded_peer_ids=frozenset()):
    """Within-patient claim neighbors. Similarity is not a label or evidence test."""
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), min_df=2, max_features=30000, dtype=np.float32)
    x = vectorizer.fit_transform([r["claim"] for r in pool])
    by_patient = defaultdict(list)
    for i, r in enumerate(pool):
        by_patient[r["sid"]].append(i)
    out = {}
    for indices in by_patient.values():
        local = (x[indices] @ x[indices].T).toarray()
        for a, i in enumerate(indices):
            candidates = [(float(local[a, b]), pool[j]["id"], j) for b, j in enumerate(indices) if pool[j]["GT"] != pool[i]["GT"] and pool[j]["id"] not in excluded_peer_ids]
            cross_s = [v for v in candidates if (pool[v[2]]["GT"] == LABELS[0]) != (pool[i]["GT"] == LABELS[0])]
            boundary = [v for v in candidates if pool[v[2]]["GT"] in LABELS[1:] and pool[i]["GT"] in LABELS[1:]]
            best = max(candidates, default=(0., None, None))
            best_s = max(cross_s, default=(0., None, None))
            best_boundary = max(boundary, default=(0., None, None))
            out[pool[i]["id"]] = dict(nearest_other_GT_id=best[1], nearest_other_GT_similarity=best[0],
                nearest_S_nonS_id=best_s[1], nearest_S_nonS_similarity=best_s[0],
                nearest_NS_NA_id=best_boundary[1], nearest_NS_NA_similarity=best_boundary[0])
    return out


def enrich(pool, teachers):
    review = {r["id"]:r for r in rows(ROOT / ".local_models/104_supervision_evidence/review_joined.jsonl")}
    retained = {r["id"] for r in rows(ROOT / ".local_models/104_supervision_evidence/paired/label_only.jsonl")}
    original512 = {r["id"] for r in rows(ROOT / "outputs/103_lora_selection/train512_ids.jsonl")}
    teacher_map = defaultdict(list)
    additional_path=OUT/'data_additional_isolation.jsonl'
    additional={r['id']:r for r in rows(additional_path)} if additional_path.exists() else {}
    lookup={r['id']:r for r in pool}
    for pid,record in additional.items():
        assert pid in lookup and record['sid']==lookup[pid]['sid'] and record['GT']==lookup[pid]['GT']
        assert record['reference_sha256']==digest(lookup[pid]['reference'])
    for pid, rater, model, prediction, reference_id in teachers:
        teacher_map[pid].append(dict(rater=rater, model=model, prediction=prediction, reference_id=reference_id))
    tokpath = ROOT / ".local_models/103_lora_selection/models/qwen3.5-9b"
    metadata = read(ROOT / "outputs/103_lora_selection/model_metadata.json")["qwen3.5-9b"]
    for name in ("tokenizer.json", "tokenizer_config.json", "chat_template.jinja"):
        assert sha(tokpath / name) == metadata["files"][name]["sha256"]
    cache = read(PRIVATE / "data_token_lengths.json")
    assert cache["source_sha256"] == sha(ROOT / ".local_models/103_lora_selection/eligible.jsonl")
    assert cache["tokenizer_files"] == {name:sha(tokpath/name) for name in ("tokenizer.json", "tokenizer_config.json", "chat_template.jinja")}
    token_lengths = {r["id"]:r for r in cache["lengths"]}
    assert set(token_lengths) == {r["id"] for r in pool}
    neighbors = neighbor_index(pool, {pid for pid,rv in review.items() if rv["final_status"]=="reference_gap"}|set(additional))
    indexed = []
    for r in pool:
        pid = r["id"]
        ts = teacher_map[pid]
        r1 = [t for t in ts if t["rater"] == "v1.1.0-rater-121"]
        assert len(r1) == 1 and r1[0]["prediction"] == r["paper_r1"]
        counts = Counter(t["prediction"] for t in ts)
        rv = review.get(pid)
        lengths = token_lengths[pid]
        assert lengths["claim_sha256"] == digest(r["claim"]) and lengths["reference_sha256"] == digest(r["reference"])
        i = {k:r[k] for k in ("id", "sid", "GT", "author", "paper_r1", "reference_id", "role", "proposition_type")}
        i.update(claim_sha256=digest(r["claim"]), reference_sha256=digest(r["reference"]),
            claim_tokens=lengths["claim_tokens"], reference_tokens=lengths["reference_tokens"],
            input_tokens=lengths["input_tokens"], input_token_sha256=lengths["input_token_sha256"],
            claim_characters=len(r["claim"]), reference_characters=len(r["reference"]),
            same_reference_teacher_N=len(ts), same_reference_teacher_predictions=dict(counts),
            teacher_S_fraction=counts[LABELS[0]] / len(ts),
            teacher_NS_NA_mixed=counts[LABELS[1]] > 0 and counts[LABELS[2]] > 0,
            original103_512=pid in original512, retained104=pid in retained,
            semantic104_status=rv["final_status"] if rv else "not_reviewed104",
            additional106_current_input_gap=pid in additional,
            independent104_verdict=rv["independent_verdict"] if rv else None,
            issue_tags104=rv["issue_tags"] if rv else [],
            original104_full_reference_read=rv["full_reference_read"] if rv else False,
            **neighbors[pid])
        indexed.append(i)
    return indexed, review


def score(r):
    if r["GT"] == LABELS[0]:
        return (r["nearest_S_nonS_similarity"], float(r["paper_r1"] != LABELS[0]), digest(SEED + r["id"]))
    # Prioritize distinct, observable difficulty proxies, never an invented GT.
    return (int(r["paper_r1"] == LABELS[0]), r["teacher_S_fraction"],
            int(r["teacher_NS_NA_mixed"]), r["nearest_S_nonS_similarity"], digest(SEED + r["id"]))


def select_dispersed(candidates, n):
    groups = defaultdict(list)
    for r in candidates:
        groups[r["sid"]].append(r)
    for group in groups.values():
        group.sort(key=score, reverse=True)
    patient_order = sorted(groups, key=lambda x:digest(SEED + "patient/" + x))
    selected = []
    while len(selected) < n:
        progressed = False
        for sid in patient_order:
            if groups[sid] and len(selected) < n:
                selected.append(groups[sid].pop(0))
                progressed = True
        assert progressed, "Insufficient eligible training examples"
    return selected


def prepare_candidates(pool, index):
    lookup = {r["id"]:r for r in pool}
    eligible = [r for r in index if r["semantic104_status"] != "reference_gap" and not r['additional106_current_input_gap']]
    selected = []
    for gt in LABELS[1:]:
        # Explicit coverage of both risks: these are existing published teacher
        # predictions, never current-9B training errors or semantic certification.
        for bucket, quota in (("teacher_S", 64), ("teacher_NS_NA_swap", 32)):
            candidates = [r for r in eligible if r["GT"]==gt and
                (r["paper_r1"]==LABELS[0] if bucket=="teacher_S" else r["paper_r1"] in LABELS[1:] and r["paper_r1"]!=gt)]
            count=min(len(candidates),quota)
            chosen=select_dispersed(candidates,count)
            for r in chosen:r["boundary_selection_bucket"]=bucket
            selected+=chosen
            if count<quota:
                already={r["id"] for r in selected}
                fallback=select_dispersed([r for r in eligible if r["GT"]==gt and r["id"] not in already],quota-count)
                for r in fallback:r["boundary_selection_bucket"]=bucket+"_insufficient_fallback"
                selected+=fallback
    # The positive protections must be neighbors of the actual selected 192
    # nonS rows, not merely neighbors of some unrelated nonS in the full pool.
    byid={r["id"]:r for r in eligible}
    positive_ids={r["nearest_S_nonS_id"] for r in selected if r["nearest_S_nonS_similarity"]>0 and r["nearest_S_nonS_id"] in byid}
    positives=[byid[pid] for pid in sorted(positive_ids)]
    assert len(positives)<=QUOTAS[LABELS[0]] and all(r["GT"]==LABELS[0] for r in positives)
    for r in positives:r["boundary_selection_bucket"]="nearest_real_S_for_selected_nonS"
    remaining=select_dispersed([r for r in eligible if r["GT"]==LABELS[0] and r["id"] not in positive_ids],QUOTAS[LABELS[0]]-len(positives))
    for r in remaining:r["boundary_selection_bucket"]="remaining_S_lexical_neighbor"
    selected+=positives+remaining
    # Exactly match patient x physician class x source and coarse token-length
    # quartile. This constrains the ordinary sample without seeing any dev score.
    bounds = {g:np.quantile([r["input_tokens"] for r in eligible if r["GT"] == g], [.25, .5, .75]).tolist() for g in LABELS}
    for r in index:
        r["length_quartile"] = int(np.searchsorted(bounds[r["GT"]], r["input_tokens"], side="right"))
    stratum = lambda r:(r["sid"], r["GT"], r["author"], r["length_quartile"], r["semantic104_status"])
    needed = Counter(stratum(r) for r in selected)
    ordinary = []
    for key, n in sorted(needed.items()):
        choices = sorted([r for r in eligible if stratum(r) == key], key=lambda r:digest("106/ordinary_sample/v1/" + r["id"]))
        assert len(choices) >= n
        ordinary += choices[:n]
    assert Counter(stratum(r) for r in ordinary) == Counter(stratum(r) for r in selected)
    datasets = {}
    for arm, values in (("ordinary_sample", ordinary), ("boundary_cover", selected)):
        # Paired strata occupy identical sequence slots, with hash ordering inside
        # a stratum; the only experimental change is which real examples fill it.
        by_slot = defaultdict(list)
        for meta in values:
            by_slot[stratum(meta)].append(meta)
        shuffled_slots = []
        for key, group in sorted(by_slot.items()):
            for ordinal, meta in enumerate(sorted(group, key=lambda r:digest("106/within_stratum/v1/" + r["id"]))):
                slot = json.dumps([list(key), ordinal], separators=(",", ":"))
                shuffled_slots.append((digest("106/training_order/v1/" + slot), meta))
        values[:] = [meta for _, meta in sorted(shuffled_slots, key=lambda item:item[0])]
        data = []
        manifest = []
        for position, meta in enumerate(values):
            source = lookup[meta["id"]]
            answer = json.dumps({"verdict":source["GT"]}, ensure_ascii=False, separators=(",", ":"))
            row = {k:source[k] for k in ("id", "sid", "GT", "author", "paper_r1", "claim", "reference", "reference_id", "role")}
            row.update(reference_sha256=meta["reference_sha256"], answer=answer, answer_text=answer,
                       messages=messages(source["claim"], source["reference"]),
                       metadata=dict(task=106, arm=arm, source="103_train40_original_pool", original_GT_unchanged=True,
                                     semantic104_status=meta["semantic104_status"], selection_proxy_only=True,
                                     prepared_candidate_not_selected_next_GPU=True))
            data.append(row)
            manifest.append(dict(meta, arm=arm, position=position, answer_sha256=digest(answer),
                                 stratum=list(stratum(meta)), teacher_agreement_required=False))
        assert len(data) == 512 and len({r["id"] for r in data}) == 512
        assert Counter(r["GT"] for r in data) == QUOTAS
        putl(PRIVATE / f"{arm}.jsonl", data)
        putl(OUT / f"data_{arm}_manifest.jsonl", manifest)
        datasets[arm] = values
    return datasets, bounds


def selected_pairs(values, byid):
    selected_ids={r["id"] for r in values}
    result=[]
    for r in values:
        if r["GT"]==LABELS[0]:continue
        for kind,peer_key,similarity_key in (("S_nonS","nearest_S_nonS_id","nearest_S_nonS_similarity"),
                ("NS_NA","nearest_NS_NA_id","nearest_NS_NA_similarity")):
            peer_id=r[peer_key]
            if peer_id is None:continue
            peer=byid[peer_id]
            result.append(dict(kind=kind,nonS_id=r["id"],nonS_GT=r["GT"],peer_id=peer_id,peer_GT=peer["GT"],
                sid=r["sid"],peer_in_same_dataset=peer_id in selected_ids,similarity=r[similarity_key],
                same_patient=r["sid"]==peer["sid"],same_reference=r["reference_id"]==peer["reference_id"],
                nonS_reference_sha256=r["reference_sha256"],peer_reference_sha256=peer["reference_sha256"],
                claim_only_lexical_pair_not_certified_clinical_minimal_pair=True))
    return result


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    pool, roles, teachers = source_pool()
    index, review = enrich(pool, teachers)
    datasets, bounds = prepare_candidates(pool, index)
    byid = {r["id"]:r for r in index}
    hard16 = [dict(byid[pid], actual_destination104=("retained" if byid[pid]["retained104"] else "isolated"),
                   included106={arm:pid in {r["id"] for r in values} for arm,values in datasets.items()},
                   semantic106_status="not_reaudited; use prior record only")
              for pid, rv in review.items() if rv["independent_verdict"] == LABELS[0] and rv["GT"] in LABELS[1:]]
    putl(OUT / "data_104_supported_disagreements.jsonl", hard16)
    putl(OUT / "data_pool_index.jsonl", index)
    putl(PRIVATE / "training_pool.jsonl", pool)
    gap = [r for r in index if r["semantic104_status"] == "reference_gap"]
    isolation=[dict(id=r["id"], sid=r["sid"], GT=r["GT"],
        reason="104 recorded reference_gap; no new interpretation or automatic restoration", reference_sha256=r["reference_sha256"]) for r in gap]
    isolation += rows(OUT/'data_additional_isolation.jsonl') if (OUT/'data_additional_isolation.jsonl').exists() else []
    putl(OUT/'data_isolation.jsonl',isolation)
    strata = lambda r:(r["sid"], r["GT"], r["author"], r["length_quartile"], r["semantic104_status"])
    comparisons = dict(full_pool=distribution(index), original103_512=distribution(r for r in index if r["original103_512"]),
        retained104_196=distribution(r for r in index if r["retained104"]),
        isolated104=distribution(r for r in index if r["semantic104_status"] in ("unresolved", "reference_gap")),
        unreviewed104_224S=distribution(r for r in index if r["original103_512"] and r["semantic104_status"] == "not_reviewed104"),
        **{arm:distribution(values) for arm, values in datasets.items()})
    ids = {arm:{r["id"] for r in values} for arm, values in datasets.items()}
    pair_summary={}
    for arm,values in datasets.items():
        pairs=selected_pairs(values,byid)
        putl(OUT/f"data_{arm}_pairs.jsonl",pairs)
        pair_summary[arm]={kind:dict(neighbor_links=sum(p["kind"]==kind for p in pairs),
            both_ends_selected=sum(p["kind"]==kind and p["peer_in_same_dataset"] for p in pairs),
            selected_similarity=stats([p["similarity"] for p in pairs if p["kind"]==kind and p["peer_in_same_dataset"]]) if any(p["kind"]==kind and p["peer_in_same_dataset"] for p in pairs) else None,
            selected_same_reference=sum(p["kind"]==kind and p["peer_in_same_dataset"] and p["same_reference"] for p in pairs)) for kind in ("S_nonS","NS_NA")}
    matching = dict(N=512, quotas=QUOTAS, both_train_patients=40,
        exact_patient_class_author_length_quartile_matching=Counter(map(strata,datasets["ordinary_sample"])) == Counter(map(strata,datasets["boundary_cover"])),
        exact_patient_class_author_length_quartile_existing104_status_matching=True,
        length_quartile_boundaries=bounds, overlap_N=len(ids["ordinary_sample"] & ids["boundary_cover"]),
        ordinary_selection="Within exact patient x GT x author x length-quartile x existing104-status quota, independent fixed SHA256 ranking; overlap allowed and disclosed",
        boundary_selection="Each nonS class:64 existing paper-R1 S predictions+32 existing paper-R1 NS/NA swaps; round-robin patients and fixed teacher/lexical ranking within bucket; include nearest real S of each actually selected nonS, fill S320 by dispersed lexical ranking",
        fixed_nonS_buckets_per_class=dict(teacher_S=64,teacher_NS_NA_swap=32),
        selected_buckets=dict(Counter(r.get("boundary_selection_bucket") for r in datasets["boundary_cover"])),
        pair_coverage=pair_summary,
        current_reference_semantic_validation=False, teacher_errors_are_difficulty_proxies=True,
        own_original_reference_each_row=True, original_GT_modified=False, synthetic_examples=0,
        known_reference_gaps_excluded=len(gap), original104_supported_disagreements_N=len(hard16),
        additional106_current_input_gaps_excluded=sum(r['additional106_current_input_gap'] for r in index),
        original104_supported_disagreements_GT=dict(Counter(r["GT"] for r in hard16)),
        excluded_confirmation_clinical_text_read=False, dev_outcomes_used_for_sampling=False,
        teacher_agreement_required=False, new_API_calls=0, GPU_calls=0)
    matching.update(prepared_candidate_only=True,selected_for_next_GPU=False,
        next_GPU_decision='Main decision: isolate fixed target-length objective factor first; 512 candidates retained for future data research, not the next actual GPU training arms',
        fixed_pair_audit_does_not_certify_all_neighbors=True)
    put(OUT / "data_summary.json", comparisons)
    put(OUT / "data_matching.json", matching)
    granular=[]
    for scope,subset in (("full_pool",index),("retained104_196",[r for r in index if r["retained104"]]),*datasets.items()):
        grouped=defaultdict(list)
        for r in subset:grouped[(r["sid"],r["GT"],r["author"])].append(r)
        granular += [dict(scope=scope,sid=key[0],GT=key[1],author=key[2],N=len(values),
            input_tokens=sum(r["input_tokens"] for r in values),mean_input_tokens=statistics.mean(r["input_tokens"] for r in values)) for key,values in sorted(grouped.items())]
    putl(OUT/"data_patient_class_source.jsonl",granular)
    duplicate_groups=defaultdict(list)
    for source in pool:duplicate_groups[digest(" ".join(source["claim"].lower().split()))].append(source)
    putl(OUT/"data_repeated_claims.jsonl",[dict(normalized_claim_sha256=key,ids=[r["id"] for r in values],
        patients=len({r["sid"] for r in values}),GT=dict(Counter(r["GT"] for r in values)),
        references=len({r["reference_id"] for r in values}),automatically_removed=False,
        note="Repeated claim strings can have different actual references; no inherited or revised labels")
        for key,values in duplicate_groups.items() if len(values)>1])
    source_paths = [ROOT / ".local_models/103_lora_selection/eligible.jsonl", ROOT / "outputs/103_lora_selection/patient_roles.json",
                    ROOT / ".local_models/104_supervision_evidence/review_joined.jsonl", PRIVATE/'data_token_lengths.json',
                    ROOT/'tasks/106_label_preparation/data_token_lengths106.py',OUT/'data_additional_isolation.jsonl',Path(__file__)]
    put(OUT / "data_manifest.json", dict(source_files={p.relative_to(ROOT).as_posix():sha(p) for p in source_paths},
        private_files={f".local_models/106_label_preparation/{arm}.jsonl":sha(PRIVATE / f"{arm}.jsonl") for arm in datasets},
        output_files={p.name:sha(p) for p in OUT.glob("data_*.json*") if p.name != "data_manifest.json"},
        expected_train_patients=roles["train"], excluded_patient_roles=["selection", "confirmation"],
        original_clinical_source_returned_to_model_context=False, source_verification="Original claim/subject/author/GT/reference checked by local filtered joins against raw files; only train40 rows returned locally"))
    print(json.dumps(dict(N=len(index), GT=comparisons["full_pool"]["GT"], hard16=len(hard16), known_gap=len(gap),
        candidates={arm:dict(N=len(v),input_tokens=sum(r["input_tokens"] for r in v)) for arm,v in datasets.items()},
        exact_matching=matching["exact_patient_class_author_length_quartile_matching"], overlap=matching["overlap_N"])))


if __name__ == "__main__":
    main()
