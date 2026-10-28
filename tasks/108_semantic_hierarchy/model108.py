"""Small semantic hierarchy heads over shared pretrained window features.

Label order is Supported, Not Supported, Not Addressed. The conditional head
is trained only for addressed cases through the ordinary joint NLL; this is
neither an auxiliary loss nor an inference threshold/postprocessing rule.
"""
import torch
from torch import nn
from torch.nn import functional as F


MODES = ('flat_ce', 'hier_shared', 'hier_pool')


def grouped_pool(features, groups, attention):
    """Vectorized softmax attention inside each contiguous bag ID."""
    if features.ndim != 2 or groups.ndim != 1 or len(groups) != len(features) or not len(groups):
        raise ValueError('Expected nonempty [windows, hidden] and one bag ID per window')
    if groups.dtype != torch.long or bool((groups < 0).any()):
        raise ValueError('Bag IDs must be nonnegative int64')
    count = int(groups.max()) + 1
    scores = attention(features).squeeze(-1)
    maxima = scores.new_full((count,), -torch.inf)
    maxima.scatter_reduce_(0, groups, scores, reduce='amax', include_self=True)
    if not bool(torch.isfinite(maxima).all()):
        raise ValueError('Every bag from0 through max(group) must have a window')
    exponent = (scores - maxima[groups]).exp()
    totals = scores.new_zeros(count).scatter_add_(0, groups, exponent)
    weights = exponent / totals[groups]
    result = features.new_zeros((count, features.shape[-1]))
    result.index_add_(0, groups, features * weights[:, None])
    return result


class Head(nn.Module):
    def __init__(self, mode='flat_ce', hidden_size=1024, dropout=.1):
        super().__init__()
        if mode not in MODES:
            raise ValueError('Unknown fixed head mode: ' + str(mode))
        self.mode = mode
        self.norm = nn.LayerNorm(hidden_size)
        self.attention = nn.Linear(hidden_size, 1)
        self.dropout = nn.Dropout(dropout)
        if mode == 'flat_ce':
            self.classifier = nn.Linear(hidden_size, 3)
        else:
            if mode == 'hier_pool':
                self.conditional_attention = nn.Linear(hidden_size, 1)
            self.addressed = nn.Linear(hidden_size, 1)
            self.conditional = nn.Linear(hidden_size, 1)

    def branch_logits(self, windows, groups):
        normalized = self.norm(windows)
        pooled = grouped_pool(normalized, groups, self.attention)
        if self.mode == 'flat_ce':
            return self.classifier(self.dropout(pooled))
        if self.mode == 'hier_shared':
            shared = self.dropout(pooled)
            return self.addressed(shared).squeeze(-1), self.conditional(shared).squeeze(-1)
        conditional = grouped_pool(normalized, groups, self.conditional_attention)
        return self.addressed(self.dropout(pooled)).squeeze(-1), self.conditional(self.dropout(conditional)).squeeze(-1)

    def forward(self, windows, group_ids=None):
        single = group_ids is None
        if single:
            group_ids = torch.zeros(len(windows), dtype=torch.long, device=windows.device)
        branches = self.branch_logits(windows, group_ids)
        if self.mode == 'flat_ce':
            result = F.log_softmax(branches.float(), dim=-1)
        else:
            a, c = (value.float() for value in branches)
            result = torch.stack((F.logsigmoid(a) + F.logsigmoid(c),
                                  F.logsigmoid(a) + F.logsigmoid(-c), F.logsigmoid(-a)), dim=-1)
        return result[0] if single else result


def minimal_checks():
    """Small mathematical checks immediately before real CPU classification."""
    torch.manual_seed(108027)
    features = torch.randn(7, 6)
    groups = torch.tensor([0, 0, 1, 1, 1, 2, 2])
    checks = []
    for mode in MODES:
        head = Head(mode, hidden_size=6, dropout=0.)
        log_probabilities = head(features, groups)
        torch.testing.assert_close(log_probabilities.exp().sum(-1), torch.ones(3), atol=2e-7, rtol=2e-7)
        separate = torch.stack([head(features[groups == i]) for i in range(3)])
        torch.testing.assert_close(log_probabilities, separate, atol=3e-7, rtol=3e-7)
        if mode != 'flat_ce':
            loss = F.nll_loss(log_probabilities, torch.full((3,), 2, dtype=torch.long))
            loss.backward()
            assert head.conditional.weight.grad is not None
            assert int(head.conditional.weight.grad.count_nonzero()) == 0
            if mode == 'hier_pool':
                assert int(head.conditional_attention.weight.grad.count_nonzero()) == 0
            assert float(head.addressed.weight.grad.abs().sum()) > 0
        checks.append(dict(mode=mode, normalized_joint=True, grouped_matches_per_bag=True,
                           NA_conditional_gradient_zero=mode != 'flat_ce'))
    return checks
