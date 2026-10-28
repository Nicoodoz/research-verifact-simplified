"""CPU-only actual-tokenizer verification of finalized 104 paired files.

No model weights are imported or downloaded. Reads only the 103 train-512
supervision pair and patient-ID roles. It never opens selection/confirmation
clinical text. Output token IDs and raw answer text stay private.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics

from training104 import encode_lists, load_rows, pad_batch, prompt_ids, validate_pairs

ROOT = Path(__file__).resolve().parents[2]


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class LocalTokenizer:
    """Same official Jinja + tokenizers CPU path used in task 103 inventory."""
    def __init__(self, folder):
        from tokenizers import Tokenizer
        from jinja2.sandbox import ImmutableSandboxedEnvironment
        self.folder = Path(folder)
        self.tokenizer = Tokenizer.from_file(str(self.folder / "tokenizer.json"))
        self.tokenizer.no_truncation()
        self.tokenizer.no_padding()
        env = ImmutableSandboxedEnvironment(trim_blocks=True, lstrip_blocks=True)

        def fail(message):
            raise ValueError(message)

        env.globals["raise_exception"] = fail
        self.template = env.from_string((self.folder / "chat_template.jinja").read_text(encoding="utf-8"))

    def apply_chat_template(self, messages, tokenize, **kwargs):
        text = self.template.render(messages=messages, **kwargs)
        return self.encode(text, add_special_tokens=False) if tokenize else text

    def encode(self, text, add_special_tokens=False):
        return self.tokenizer.encode(text, add_special_tokens=add_special_tokens).ids

    def decode(self, ids, skip_special_tokens=False):
        return self.tokenizer.decode(ids, skip_special_tokens=skip_special_tokens)

    def convert_tokens_to_ids(self, token):
        return self.tokenizer.token_to_id(token)


def stats(values):
    ordered = sorted(values)
    return {
        "N": len(values), "sum": sum(values), "mean": statistics.mean(values),
        "min": min(values), "median": statistics.median(values),
        "p95": ordered[min(len(ordered) - 1, int(.95 * (len(ordered) - 1)))],
        "max": max(values),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--private", type=Path, default=ROOT / ".local_models/104_supervision_evidence")
    parser.add_argument("--pair-dir", type=Path, help="Explicit paired or candidate_paired input folder; candidate data require this explicit path.")
    parser.add_argument("--tokenizer", type=Path, default=ROOT / ".local_models/103_lora_selection/models/qwen3.5-9b")
    parser.add_argument("--output", type=Path, default=ROOT / "outputs/104_supervision_evidence/token_summary.json")
    args = parser.parse_args()
    roles = json.loads((ROOT / "outputs/103_lora_selection/patient_roles.json").read_text(encoding="utf-8-sig"))["patients"]
    if args.pair_dir is not None:
        pair_dir = args.pair_dir
    elif (args.private / "paired/label_only.jsonl").is_file():
        pair_dir = args.private / "paired"
    elif (args.private / "label_only.jsonl").is_file():
        pair_dir = args.private
    else:
        raise FileNotFoundError("No finalized pair found; explicitly pass --pair-dir for candidate_paired checks")
    label_path, brief_path = pair_dir / "label_only.jsonl", pair_dir / "evidence_brief.jsonl"
    labels, briefs = load_rows(label_path), load_rows(brief_path)
    check = validate_pairs(labels, briefs, set(roles["train"]), set(roles["selection"]) | set(roles["confirmation"]))
    meta = json.loads((ROOT / "outputs/103_lora_selection/model_metadata.json").read_text(encoding="utf-8-sig"))["qwen3.5-9b"]
    for name in ("tokenizer.json", "tokenizer_config.json", "chat_template.jinja"):
        if file_sha(args.tokenizer / name) != meta["files"][name]["sha256"]:
            raise ValueError("Tokenizer revision does not match task 103")
    tok = LocalTokenizer(args.tokenizer)
    lengths = []
    for label, brief in zip(labels, briefs):
        left, right = encode_lists(tok, label), encode_lists(tok, brief)
        prefix_left, prefix_right = prompt_ids(tok, label), prompt_ids(tok, brief)
        assert prefix_left == prefix_right
        for ids, loss_labels, supervised in (left, right):
            prefix_n = len(ids) - supervised
            assert loss_labels[:prefix_n] == [-100] * prefix_n
            assert loss_labels[prefix_n:] == ids[prefix_n:]
        batch = pad_batch([left, right], tok.convert_tokens_to_ids("<|endoftext|>"))
        for mask, loss_labels in zip(batch["attention_mask"], batch["labels"]):
            assert all(target == -100 for active, target in zip(mask, loss_labels) if not active)
        relation = json.loads(brief["answer"])["relation"]
        lengths.append({
            "id": label["id"], "sid": label["sid"], "GT": label["GT"], "author": label["author"],
            "input_tokens": len(prefix_left), "label_answer_tokens": left[2], "brief_answer_tokens": right[2],
            "label_total_tokens": len(left[0]), "brief_total_tokens": len(right[0]),
            "added_answer_tokens": right[2] - left[2], "relation_words": len(relation.split()),
            "prompt_token_ids_sha256": hashlib.sha256(json.dumps(prefix_left, separators=(",", ":")).encode()).hexdigest(),
        })
    private_out = args.private / "training_token_lengths.jsonl"
    private_out.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in lengths), encoding="utf-8")
    summary = {
        "model": "qwen3.5-9b", "revision": meta["revision"], "checks": check,
        "CPU_only": True, "model_weights_loaded": False, "new_API_calls": 0,
        "input_pair_folder": pair_dir.name,
        "candidate_only": pair_dir.name.startswith("candidate_"),
        "loss_mask_prompt_and_padding": "-100", "answer_and_end_message_supervised": True,
        "input_unchanged_across_arms": True, "GT_is_metadata_not_a_prompt_field": True,
        "lengths": {key: stats([r[key] for r in lengths]) for key in (
            "input_tokens", "label_answer_tokens", "brief_answer_tokens", "label_total_tokens",
            "brief_total_tokens", "added_answer_tokens", "relation_words")},
        "GT": dict(Counter(row["GT"] for row in labels)),
        "author": dict(Counter(row["author"] for row in labels)),
        "relation_target_50_to_100_words": sum(50 <= row["relation_words"] <= 100 for row in lengths),
        "target_is_guidance_not_forced_padding": True,
        "source_files": {"label_only_sha256": file_sha(label_path), "evidence_brief_sha256": file_sha(brief_path),
                         "private_lengths_sha256": file_sha(private_out)},
        "tokenizer_files": {name: file_sha(args.tokenizer / name) for name in ("tokenizer.json", "tokenizer_config.json", "chat_template.jinja")},
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
