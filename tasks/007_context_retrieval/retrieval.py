"""Deterministic lexical retrieval probe; NOT a reconstruction of VeriFact's index."""
from collections import Counter
import math
import re
import numpy as np

ARMS = ("claim", "sentence", "local", "mixed")
STOP = set("a an the this that these those is are was were be been being of to and or in on at for from by with as it its he she his her they their patient patients pt had has have did does do will would can could should no not".split()) - {"no", "not"}


def tokens(text):
    # Remove deidentification placeholder labels, retain their visible numeric values.
    text = re.sub(r"\[\*\*(.*?)\*\*\]", lambda m: " ".join(re.findall(r"\d+", m.group(1))), text)
    result = re.findall(r"[a-z]+|\d+(?:\.\d+)?", text.lower())
    return [str(int(t)) if t.isdigit() else t for t in result if t not in STOP]


def spans(text, limit=640):
    """Nonoverlapping raw EHR paragraph spans, split at whitespace if too long."""
    edges, offset = [], 0
    for separator in re.finditer(r"\n[ \t\r]*\n", text):
        edges.append((offset, separator.start()))
        offset = separator.end()
    edges.append((offset, len(text)))
    for start, end in edges:
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end-1].isspace():
            end -= 1
        while end-start > limit:
            candidates = list(re.finditer(r"\s+", text[start+limit//2:start+limit]))
            stop = start+limit//2+candidates[-1].start() if candidates else start+limit
            yield start, stop
            start = stop
            while start < end and text[start].isspace():
                start += 1
        if start < end:
            yield start, end


def sentence_query(claim, parent, sentences):
    choices = sorted({s["text"] for s in sentences if s["text"] and s["text"] in parent})
    if not choices:
        return parent, "parent_fallback_no_literal_sentence"
    own = set(tokens(claim))
    def score(text):
        other = set(tokens(text))
        return len(own & other)/max(1, len(own | other))
    selected = min(choices, key=lambda t: (-score(t), len(t), t))
    return selected, "literal_sentence_max_token_jaccard_no_GT"


class BM25:
    def __init__(self, passages):
        self.passages = passages
        counts = [Counter(tokens(p["search_text"])) for p in passages]
        self.lengths = np.array([sum(c.values()) for c in counts], dtype=float)
        self.average = float(self.lengths.mean()) if len(counts) else 1
        self.postings = {}
        for i, own in enumerate(counts):
            for term, tf in own.items():
                self.postings.setdefault(term, []).append((i, tf))

    def rank(self, query):
        scores = np.zeros(len(self.passages))
        # Binary query terms keep query repetition from being an implicit weight.
        for term in set(tokens(query)):
            entries = self.postings.get(term, [])
            if not entries:
                continue
            idf = math.log(1+(len(self.passages)-len(entries)+.5)/(len(entries)+.5))
            for i, tf in entries:
                scores[i] += idf * (tf*2.2)/(tf+1.2*(.25+.75*self.lengths[i]/max(1,self.average)))
        return [(i, float(scores[i])) for i in sorted(range(len(scores)), key=lambda i: (-scores[i], self.passages[i]["passage_id"])) if scores[i] > 0]


def retrieve(index, queries, budget=9000, max_items=24):
    rankings = {arm:index.rank(queries[arm]) for arm in ("claim", "sentence", "local")}
    combined = Counter()
    for arm in ("claim", "local"):
        for rank, (i, _) in enumerate(rankings[arm][:100], 1):
            combined[i] += 1/(60+rank)
    rankings["mixed"] = sorted(combined.items(), key=lambda t:(-t[1], index.passages[t[0]]["passage_id"]))
    def pack(ranking, cap):
        picked, size, texts = [], 0, set()
        for rank, (i, score) in enumerate(ranking[:100], 1):
            passage = index.passages[i]
            # Preserve repeated events at different dates; remove only same exact text/date/category.
            duplicate = (passage["date"], passage["category"], passage["text"])
            if duplicate in texts:
                continue
            cost = len(reference_line(len(picked)+1, passage))+1
            if size+cost > cap:
                empty = dict(passage,text="")
                remaining = cap-size-len(reference_line(len(picked)+1,empty))-12
                if remaining < 80:
                    continue
                raw = passage["text"][:remaining]
                if " " in raw:
                    raw = raw.rsplit(" ",1)[0]
                passage = dict(passage,text=raw,original_end_exclusive=passage["end_exclusive"],
                    end_exclusive=passage["start"]+len(raw),display_truncated_for_budget=True)
                cost = len(reference_line(len(picked)+1,passage))+1
                if size+cost > cap:
                    continue
            picked.append(dict(passage, retrieval_rank=rank, score=score))
            texts.add(duplicate)
            size += cost
            if len(picked) == max_items:
                break
        return picked, size
    # Match the available evidence character budget within each claim, not just a shared ceiling.
    common_budget = min(pack(r, budget)[1] for r in rankings.values())
    outputs = {}
    for arm, ranking in rankings.items():
        picked, size = pack(ranking, common_budget)
        outputs[arm] = dict(passages=picked, retrieved_characters=size, matched_character_budget=common_budget,
            top100=[dict(passage_id=index.passages[i]["passage_id"], score=s) for i,s in ranking[:100]])
    return outputs


def reference_line(number, p):
    return (f"{number}. Date: {p['date']}, Time: {p['time']}, Note Category: {p['category']}, "
        f"Note ID: {p['note_id']}, Raw characters: [{p['start']},{p['end_exclusive']}) | Text: {p['text']}")


def reference(result, admission):
    ordered = sorted(result["passages"], key=lambda p:(p["date"],p["time"],p["note_id"],p["start"]))
    result["reference_passage_ids"] = [p["passage_id"] for p in ordered]
    header = f"Hospital Admission Start: {admission['ADMITTIME']}\nHospital Admission End: {admission['DISCHTIME']}\nElectronic Health Record Context\nOrdered by Time (Earliest to Latest):\n"
    return header + ("\n".join(reference_line(i,p) for i,p in enumerate(ordered,1)) or "No Electronic Health Record Context Found.")
