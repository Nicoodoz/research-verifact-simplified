"""Meaningful synthetic interface checks; no patient input or model loading."""
from copy import deepcopy
import json
import unittest

from training104 import canonical, checkpoint_due, digest, encode_lists, messages, optimizer_batches, pad_batch, parse_answer, validate_pairs


class CharacterTokenizer:
    """Transparent loss-mask fixture, independently inspectable token identities."""
    def apply_chat_template(self, messages, tokenize, **kwargs):
        assert kwargs["enable_thinking"] is False
        return self.encode("\n".join(message["content"] for message in messages))

    def encode(self, text, add_special_tokens=False):
        return [ord(char) for char in text]

    def decode(self, ids, skip_special_tokens=False):
        return "".join(chr(value) for value in ids)

    def convert_tokens_to_ids(self, token):
        return 1 if token == "<|im_end|>" else 0


def paired():
    reference = "On Monday the synthetic marker was elevated. On Tuesday it improved but remained elevated."
    quote = "improved but remained elevated"
    start = reference.index(quote)
    base = {"id": "fixture-104", "sid": "training-fixture", "author": "human", "GT": "Not Supported",
            "claim": "The synthetic marker fully normalized on Tuesday.", "reference": reference,
            "reference_id": "fixture-reference", "reference_sha256": digest(reference)}
    label, brief = deepcopy(base), deepcopy(base)
    label["answer"] = canonical({"verdict": base["GT"]})
    brief["answer"] = canonical({"evidence": [quote], "relation": "The Tuesday measurement improved but was still elevated. Improvement does not establish full normalization.", "verdict": base["GT"]})
    brief["evidence_spans"] = [{"start": start, "end": start + len(quote), "text": quote}]
    return label, brief


class Training104Tests(unittest.TestCase):
    def test_only_answer_changes_with_identical_prompt_and_GT_metadata(self):
        label, brief = paired()
        check = validate_pairs([label], [brief], {"training-fixture"}, {"excluded-fixture"})
        self.assertEqual(check["N"], 1)
        self.assertEqual(messages(label["claim"], label["reference"]), messages(brief["claim"], brief["reference"]))
        # Changing metadata cannot change prompt text; output-label definitions are not GT leakage.
        changed = deepcopy(label)
        changed["GT"] = "Supported"
        self.assertEqual(messages(label["claim"], label["reference"]), messages(changed["claim"], changed["reference"]))
        payload = messages(label["claim"], label["reference"])[1]["content"].split("## Input JSON:\n", 1)[1]
        self.assertEqual(set(json.loads(payload)), {"text", "reference"})

    def test_entire_answer_and_EOS_have_loss_prompt_and_padding_do_not(self):
        label, brief = paired()
        encoded = [encode_lists(CharacterTokenizer(), row) for row in (label, brief)]
        for row, (ids, targets, supervised) in zip((label, brief), encoded):
            self.assertEqual(targets[-supervised:-1], [ord(c) for c in row["answer"]])
            self.assertEqual(targets[-1], 1)
            self.assertTrue(all(value == -100 for value in targets[:-supervised]))
            self.assertEqual(ids[-supervised:], targets[-supervised:])
        batch = pad_batch(encoded, 0)
        self.assertTrue(any(not m for m in batch["attention_mask"][0]))
        for masks, targets in zip(batch["attention_mask"], batch["labels"]):
            self.assertTrue(all(target == -100 for active, target in zip(masks, targets) if not active))

    def test_reference_or_GT_change_is_rejected(self):
        for field, value in (("GT", "Supported"), ("reference", "An unrelated source."), ("id", "other"), ("sid", "excluded-fixture")):
            label, brief = paired()
            brief[field] = value
            with self.assertRaises(ValueError):
                validate_pairs([label], [brief], {"training-fixture"}, {"excluded-fixture"})

    def test_invented_quote_offset_and_other_reference_are_rejected(self):
        for mutate in (
            lambda row: row["evidence_spans"][0].update(start=0),
            lambda row: row["evidence_spans"][0].update(reference_sha256="other"),
            lambda row: row.update(reference_sha256="other"),
        ):
            _, brief = paired()
            mutate(brief)
            with self.assertRaises(ValueError):
                parse_answer(brief, "evidence_brief")

    def test_empty_NA_evidence_permitted_without_fabricating_a_quote(self):
        label, brief = paired()
        brief["GT"] = "Not Addressed"
        brief["answer"] = canonical({"evidence": [], "relation": "The reference discusses a different synthetic event and does not address this assertion's participant or outcome.", "verdict": "Not Addressed"})
        brief["evidence_spans"] = []
        self.assertEqual(parse_answer(brief, "evidence_brief")["evidence"], [])
        brief["GT"] = "Not Supported"
        brief["answer"] = canonical({"evidence": [], "relation": "An unsupported assertion.", "verdict": "Not Supported"})
        with self.assertRaises(ValueError):
            parse_answer(brief)

    def test_duplicate_verdict_keys_or_answer_GT_override_are_rejected(self):
        label, _ = paired()
        for answer in ('{"verdict":"Supported","verdict":"Not Supported"}', '{"verdict":"Supported"}'):
            label["answer"] = answer
            with self.assertRaises(ValueError):
                parse_answer(label)

    def test_different_patient_role_and_duplicate_ID_are_rejected(self):
        label, brief = paired()
        with self.assertRaises(ValueError):
            validate_pairs([label], [brief], {"other-fixture"}, {"training-fixture"})
        with self.assertRaises(ValueError):
            validate_pairs([label, label], [brief, brief], {"training-fixture"})

    def test_non_multiple_of_eight_tail_is_not_dropped_duplicated_or_underweighted(self):
        rows=[{"id":str(i),"mean_loss":float(i+1)} for i in range(19)]
        batches=list(optimizer_batches(rows,8))
        self.assertEqual([b["microbatch_count"] for b in batches],[8,8,3])
        self.assertEqual([r["id"] for b in batches for r in b["micro_rows"]],[r["id"] for r in rows])
        self.assertEqual([b["end_sample"] for b in batches],[8,16,19])
        self.assertEqual([b["optimizer_step"] for b in batches],[1,2,3])
        self.assertEqual(sum(r["mean_loss"]/batches[-1]["loss_divisor"] for r in batches[-1]["micro_rows"]),18.)
        self.assertTrue(checkpoint_due(batches[-1]))
        self.assertFalse(checkpoint_due(batches[0]))

    def test_resume_uses_exact_consumed_offset_and_empty_completed_plan(self):
        rows=[{"id":str(i)} for i in range(19)]
        resumed=list(optimizer_batches(rows,8,start_sample=8))
        self.assertEqual([r["id"] for b in resumed for r in b["micro_rows"]],[str(i) for i in range(8,19)])
        self.assertEqual(list(optimizer_batches(rows,8,start_sample=19)),[])
        with self.assertRaises(ValueError):list(optimizer_batches(rows,8,start_sample=3))
        with self.assertRaises(ValueError):list(optimizer_batches(rows,0))
        boundary=list(optimizer_batches([{}]*259,8))
        self.assertTrue(checkpoint_due(boundary[31]))
        self.assertTrue(checkpoint_due(boundary[-1]))


if __name__ == "__main__":
    unittest.main()
