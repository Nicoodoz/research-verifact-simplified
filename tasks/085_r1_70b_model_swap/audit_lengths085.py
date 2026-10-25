"""Offline exact-tokenizer audit of frozen provider-neutral B/F4 inputs."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path

from transformers import AutoTokenizer

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/085_r1_70b_model_swap"
CACHE = ROOT / ".local_models/085a_r1_tokenizer"
LABELS = ("B", "F4")
CONTEXTS = (8192, 16384, 32768, 65536, 131072)
RESERVES = (4096, 8192)


def sha(path: Path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stable(prefix: str, value: str):
    return hashlib.sha256((prefix + value).encode("utf-8")).hexdigest()


def rows(path: Path):
    return [json.loads(s) for s in path.open(encoding="utf-8-sig") if s.strip()]


def put(path: Path, value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8",newline="\n")


def put_lines(path: Path, values):
    with path.open("w",encoding="utf-8",newline="\n") as f:
        for value in values:
            f.write(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")


def quantile(values, p):
    ordered = sorted(values)
    position = (len(ordered)-1)*p
    lo = math.floor(position)
    hi = math.ceil(position)
    return ordered[lo] + (ordered[hi]-ordered[lo])*(position-lo)


def summary(values):
    return {"min":min(values),"median":statistics.median(values),"p90":quantile(values,.90),
            "p95":quantile(values,.95),"max":max(values),"n":len(values)}


def choose_preflight(by_id):
    all_rows = list(by_id.values())
    short = min(all_rows,key=lambda r:(r["B_chat_tokens"],stable("085/shortB/v1:",r["id"]),r["id"]))
    median_f4 = statistics.median(r["F4_chat_tokens"] for r in all_rows)
    middle = min((r for r in all_rows if r["id"]!=short["id"]),
                 key=lambda r:(abs(r["F4_chat_tokens"]-median_f4),stable("085/medianF4/v1:",r["id"]),r["id"]))
    longest = min((r for r in all_rows if r["id"] not in (short["id"],middle["id"])),
                  key=lambda r:(-r["F4_chat_tokens"],stable("085/longF4/v1:",r["id"]),r["id"]))
    return [{"role":"short_B","id":short["id"],"sid":short["sid"],"arm":"B","chat_input_tokens":short["B_chat_tokens"]},
            {"role":"median_F4","id":middle["id"],"sid":middle["sid"],"arm":"F4","chat_input_tokens":middle["F4_chat_tokens"]},
            {"role":"longest_F4","id":longest["id"],"sid":longest["sid"],"arm":"F4","chat_input_tokens":longest["F4_chat_tokens"]}]


def main():
    assert (OUT/"source_manifest.json").exists()
    assert not (OUT/"tokenizer_length_audit.json").exists()
    source = json.loads((OUT/"tokenizer_source.json").read_text(encoding="utf-8"))
    for name, meta in source["files"].items():
        assert sha(CACHE/name) == meta["sha256"]
    tokenizer = AutoTokenizer.from_pretrained(CACHE,local_files_only=True,use_fast=True,trust_remote_code=False)
    assert tokenizer.is_fast and tokenizer.chat_template
    chat_template = tokenizer.chat_template
    assert isinstance(chat_template,str)
    (OUT/"chat_template.jinja").write_bytes(chat_template.encode("utf-8"))
    neutral = rows(OUT/"neutral_jobs.jsonl")
    assert len(neutral)==360
    byid=defaultdict(dict)
    lengths=[]
    for row in neutral:
        pid,arm=row["id"],row["arm"]
        assert arm in LABELS and arm not in byid[pid]
        user=json.dumps({"proposition":row["claim"],"reference":row["reference"]},ensure_ascii=False,separators=(",",":"))
        messages=[{"role":"system","content":row["instruction_semantic_content"]},{"role":"user","content":user}]
        chat_ids=tokenizer.apply_chat_template(messages,tokenize=True,add_generation_prompt=True,truncation=False)
        plain=row["instruction_semantic_content"]+"\n\n"+user
        plain_ids=tokenizer.encode(plain,add_special_tokens=False,truncation=False)
        item={"id":pid,"sid":row["sid"],"arm":arm,"chat_input_tokens":len(chat_ids),
              "plain_input_tokens":len(plain_ids),"claim_chars":len(row["claim"]),
              "reference_chars":len(row["reference"]),"system_chars":len(row["instruction_semantic_content"]),
              "source_084_body_sha256":row["source_084_body_sha256"]}
        byid[pid][arm]=item
        lengths.append(item)
    assert len(byid)==180 and all(set(v)==set(LABELS) for v in byid.values())
    put_lines(OUT/"tokenizer_lengths.jsonl",lengths)
    flat={pid:{"id":pid,"sid":byid[pid]["B"]["sid"],
               **{f"{arm}_{measure}_tokens":byid[pid][arm][f"{measure}_input_tokens"] for arm in LABELS for measure in ("chat","plain")}}
          for pid in byid}
    preflight=choose_preflight(flat)
    assert len({x["id"] for x in preflight})==3
    put(OUT/"preflight_selection.json",{"status":"FROZEN_BEFORE_ENDPOINT_AND_R1_GT",
        "selection":"shortest B; F4 nearest median; longest F4; SHA256 tie breaks; distinct IDs",
        "cases":preflight,"lengths_sha256":sha(OUT/"tokenizer_lengths.jsonl"),
        "source_neutral_sha256":sha(OUT/"neutral_jobs.jsonl"),"GT_read":False})
    windows={}
    for arm in LABELS:
        sizes=[byid[pid][arm]["chat_input_tokens"] for pid in byid]
        windows[arm]={}
        for context in CONTEXTS:
            windows[arm][str(context)]={}
            for reserve in RESERVES:
                margins=[context-n-reserve for n in sizes]
                windows[arm][str(context)][str(reserve)]={"fits_n":sum(x>=0 for x in margins),
                    "n":len(margins),"min_margin":min(margins),"median_margin":statistics.median(margins),
                    "max_excess":max(0,-min(margins))}
    config=json.loads((CACHE/"config.json").read_text(encoding="utf-8"))
    tokconfig=json.loads((CACHE/"tokenizer_config.json").read_text(encoding="utf-8"))
    result={"status":"OFFLINE_TOKENIZER_AUDIT_NO_ENDPOINT",
        "repo":source["repo"],"revision":source["revision"],"tokenizer_source_sha256":sha(OUT/"tokenizer_source.json"),
        "neutral_jobs_sha256":sha(OUT/"neutral_jobs.jsonl"),"lengths_sha256":sha(OUT/"tokenizer_lengths.jsonl"),
        "chat_template_sha256":sha(OUT/"chat_template.jinja"),"tokenizer_class":type(tokenizer).__name__,
        "tokenizer_model_max_length":tokenizer.model_max_length,
        "tokenizer_config_model_max_length":tokconfig.get("model_max_length"),
        "model_config_max_position_embeddings":config.get("max_position_embeddings"),
        "model_config_rope_scaling":config.get("rope_scaling"),
        "versions":{p:importlib.metadata.version(p) for p in ("transformers","tokenizers","huggingface_hub","jinja2","boto3")},
        "n":180,"stats":{arm:{measure:summary([byid[pid][arm][f"{measure}_input_tokens"] for pid in byid])
                           for measure in ("chat","plain")} for arm in LABELS},
        "context_assumptions":list(CONTEXTS),"output_reserves":list(RESERVES),"margins":windows,
        "no_truncation":True,"provider_context_verified":False,"weights_downloaded":False,"inference_calls":0}
    put(OUT/"tokenizer_length_audit.json",result)
    lines_md=["# R1-70B tokenizer长度审计（085A，零推理）","",
      f"官方仓库修订：`{source['revision']}`；只下载四个tokenizer/配置文件，未下载权重。",
      f"tokenizer chat template SHA-256：`{result['chat_template_sha256']}`。`add_generation_prompt=True`；没有截断。",
      "","|臂与序列化|min|median|p90|p95|max|","|---|---:|---:|---:|---:|---:|"]
    for arm in LABELS:
        for measure in ("chat","plain"):
            s=result["stats"][arm][measure]
            lines_md.append(f"|{arm} {measure}|{s['min']}|{s['median']:.1f}|{s['p90']:.1f}|{s['p95']:.1f}|{s['max']}|")
    lines_md += ["","下表为假设context下180条可放入的数量；括号是最短余量（负值为最多超出）。实际JumpStart容器限制**尚未验证**。",
                 "","|臂|context|预留4096输出|预留8192输出|","|---|---:|---:|---:|"]
    for arm in LABELS:
        for context in CONTEXTS:
            a=windows[arm][str(context)]
            lines_md.append(f"|{arm}|{context}|{a['4096']['fits_n']}/180 ({a['4096']['min_margin']})|{a['8192']['fits_n']}/180 ({a['8192']['min_margin']})|")
    lines_md += ["",f"模型`config.json`给max_position_embeddings={config.get('max_position_embeddings')}，tokenizer元数据给model_max_length={tokconfig.get('model_max_length')}；两者不同，不能据较大值假设部署端支持。",
                 "", "未来正式实验先以部署样例和A/B真实preflight确认template、context、输出预算与截断状态；不足时停止，不缩短claim、C48或F4。", ""]
    (OUT/"tokenizer_length_audit.md").write_text("\n".join(lines_md),encoding="utf-8",newline="\n")
    print(json.dumps({"chat_template_sha256":result["chat_template_sha256"],"stats":result["stats"],
                      "preflight":preflight},ensure_ascii=False))


if __name__=="__main__":
    main()
