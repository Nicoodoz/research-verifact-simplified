"""Read-only observer for one ordinary greedy generate call (CPU import safe).

Pass ``NativeBranchCapture(input_ids.shape[1], ids)`` in ``logits_processor``.
The width is the shared padded input width, not an individual unpadded length.
Call ``records()`` after generation. Reuse neither the observer nor batch rows
across generate calls; beam/speculative/streaming batch remapping is unsupported.

Transformers5.17.0 passes scores after default processors to custom processors.
Thus these are scores at this processor position, not verified raw model logits.
No prefix is forced, no tensor is modified, and the identical scores object is
returned. This does not prove unchanged outputs under a wall-clock deadline or
zero overhead: reading tensors can synchronize CUDA and affect compilation.
"""
import math

CANONICAL_PREFIX = (4754, 415, 8217, 3147)
BRANCH_TOKENS = (33490, 2536)


class NativeBranchCapture:
    def __init__(self, input_width, row_ids):
        if not isinstance(input_width, int) or input_width <= 0:
            raise ValueError('Use the positive padded input width')
        if len(set(row_ids)) != len(row_ids):
            raise ValueError('Use one unique ID per unchanged greedy batch row')
        self.input_width = input_width
        self.row_ids = tuple(row_ids)
        self.observed = False
        self._records = [dict(id=i, status='missing_prefix_step_not_reached') for i in self.row_ids]

    def __call__(self, input_ids, scores):
        # Prefix matching is anchored at generation start, never a later suffix.
        if self.observed or input_ids.shape[-1] - self.input_width != len(CANONICAL_PREFIX):
            return scores
        self.observed = True
        try:
            if input_ids.shape[0] != len(self.row_ids) or scores.shape[0] != len(self.row_ids):
                raise ValueError('Batch expansion or row remapping is unsupported')
            prefixes = input_ids[:, self.input_width:].detach().cpu().tolist()
            pairs = scores[:, list(BRANCH_TOKENS)].detach().cpu().tolist()
            for row, (prefix, pair) in enumerate(zip(prefixes, pairs)):
                record = self._records[row]
                if tuple(prefix) != CANONICAL_PREFIX:
                    record.update(status='missing_prefix_mismatch', generated_prefix_token_ids=prefix)
                    continue
                s, not_s = map(float, pair)
                if not all(math.isfinite(value) for value in (s, not_s)):
                    record.update(status='missing_nonfinite_scores')
                    continue
                record.update(status='captured', prefix_token_ids=list(CANONICAL_PREFIX),
                    branch_token_ids=dict(S=BRANCH_TOKENS[0], Not=BRANCH_TOKENS[1]),
                    branch_logits=dict(S=s, Not=not_s), logit_S_minus_Not=s-not_s,
                    score_kind='scores_at_custom_logits_processor', raw_logits_verified=False,
                    capture_position='after_default_processors_before_greedy_selection')
        except Exception as error:
            # A missing observation must not replace or interrupt a native answer.
            self._records = [dict(id=i, status='missing_capture_error', error_type=type(error).__name__)
                             for i in self.row_ids]
        return scores

    def records(self):
        """Return JSON-compatible copies, including explicit missing records."""
        return [dict(row) for row in self._records]
