"""Fixed low-capacity 083 feature blocks and fold-fitted local text encoder."""
from __future__ import annotations

import math

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

import inventory083 as base
import parse083 as structure

LABELS = ("Supported", "Not Supported", "Not Addressed")
ARMS = ("N", "C", "T", "G", "R", "P")
TEXT_DIM = 24


def numeric(scores, raw):
    if not isinstance(scores, dict):
        score = np.full(3, 1 / 3, dtype=float)
    else:
        try:
            score = np.asarray([float(scores[z]) / 100 for z in LABELS], dtype=float)
            if not np.all(np.isfinite(score)) or np.any(score < 0) or abs(score.sum() - 1) > 1e-5:
                raise ValueError("invalid scores")
        except (KeyError, TypeError, ValueError):
            score = np.full(3, 1 / 3, dtype=float)
    z = np.log(np.maximum(score, 1e-6))
    centered = z - z.mean()
    pairs = ((0, 1), (0, 2), (1, 2))
    squared = [(z[a] - z[b]) ** 2 for a, b in pairs]
    onehot = [int(raw == lab) for lab in LABELS]
    return (centered.tolist() + squared + onehot)


def build_rows():
    native = base.lines("outputs/083_native_rationale_information/native_texts.jsonl")
    cleaned = {(x["phase"], x["arm"], x["id"]): x for x in base.lines(
        "outputs/083_native_rationale_information/cleaned_inputs.jsonl")}
    parsed = {(x["phase"], x["id"]): x for x in base.lines(
        "outputs/083_native_rationale_information/structured_arguments.jsonl")}
    rows = []
    for x in native:
        if x["arm"] != "F4":
            continue
        key = (x["phase"], x["arm"], x["id"])
        c, p = cleaned[key], parsed[x["phase"], x["id"]]
        assert c["content_sha256"] == x["content_sha256"]
        assert c["cleaned_sha256"] == p["cleaned_sha256"]
        rows.append({"phase": x["phase"], "id": x["id"], "sid": x["sid"],
                     "claim": x["claim"], "rationale": c["cleaned_text"],
                     "thinking": (x["reasoning_content"] or "")[:2048],
                     "numeric": numeric(x["native_scores"], x["native_verdict"]),
                     "raw": x["native_verdict"] if x["native_verdict"] in LABELS else None,
                     "scores": x["native_scores"],
                     "coarse": p["coarse"], "fine": p["fine"],
                     "structured_accepted": len(p["accepted"]),
                     "structured_malformed": p["malformed"],
                     "body_sha256": x["body_sha256"],
                     "content_sha256": x["content_sha256"],
                     "extraction_request_id": p["extraction_request_id"]})
    assert len(rows) == 1015
    assert sum(x["phase"] == "train" for x in rows) == 459
    assert sum(x["phase"] in ("old352", "new180") for x in rows) == 532
    assert sum(x["phase"] == "repeat" for x in rows) == 24
    return rows


class LocalTextEncoder:
    """Train-fold-only TF-IDF/SVD fallback because the main env lacks torch."""

    def __init__(self, dim=TEXT_DIM):
        self.dim = dim
        self.vectorizer = None
        self.reducer = None
        self.rank = 0

    def fit(self, values):
        values = [str(x or "") for x in values]
        self.vectorizer = TfidfVectorizer(analyzer="char", ngram_range=(3, 5),
                                          min_df=2, max_features=3000, dtype=np.float32)
        x = self.vectorizer.fit_transform(values)
        self.rank = min(self.dim, max(1, min(x.shape) - 1))
        self.reducer = TruncatedSVD(n_components=self.rank, n_iter=5, random_state=83)
        self.reducer.fit(x)
        return self

    def transform(self, values):
        x = self.reducer.transform(self.vectorizer.transform([str(z or "") for z in values]))
        if self.rank < self.dim:
            x = np.pad(x, ((0, 0), (0, self.dim - self.rank)))
        return np.asarray(x, dtype=float)


class FeatureMap:
    def __init__(self):
        self.claim = LocalTextEncoder()
        self.rationale = LocalTextEncoder()
        self.thinking = LocalTextEncoder()

    def fit(self, rows):
        self.claim.fit([x["claim"] for x in rows])
        self.rationale.fit([x["rationale"] for x in rows])
        self.thinking.fit([x["thinking"] for x in rows])
        return self

    def blocks(self, rows):
        assert rows
        return {"numeric": np.asarray([x["numeric"] for x in rows], dtype=float),
                "claim": self.claim.transform([x["claim"] for x in rows]),
                "rationale": self.rationale.transform([x["rationale"] for x in rows]),
                "thinking": self.thinking.transform([x["thinking"] for x in rows]),
                "coarse": np.asarray([x["coarse"] for x in rows], dtype=float),
                "fine": np.asarray([x["fine"] for x in rows], dtype=float)}


def select(blocks, arm, coarse_override=None, fine_override=None):
    assert arm in ARMS
    order = {"N": ("numeric",), "C": ("numeric", "claim"),
             "T": ("numeric", "claim", "rationale"),
             "G": ("numeric", "claim", "coarse"),
             "R": ("numeric", "claim", "coarse", "fine"),
             "P": ("numeric", "claim", "thinking")}[arm]
    pieces = []
    for key in order:
        if key == "coarse" and coarse_override is not None:
            pieces.append(coarse_override)
        elif key == "fine" and fine_override is not None:
            pieces.append(fine_override)
        else:
            pieces.append(blocks[key])
    matrix = np.concatenate(pieces, axis=1)
    assert np.all(np.isfinite(matrix))
    return matrix
