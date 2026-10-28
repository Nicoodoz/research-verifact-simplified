"""CPU mathematical checks only; the selected 106 training loss stays 105 CE.

Complete legal-label probabilities below require the conditional probability of
EVERY token of each JSON answer and its EOS. They are not a single token score,
an LLM confidence, or recoverable from 105's saved generated text.
"""
from __future__ import annotations
import numpy as np

LABELS = ('Supported', 'Not Supported', 'Not Addressed')

def softmax(logits):
    logits = np.asarray(logits, dtype=float)
    z = np.exp(logits - logits.max(axis=-1, keepdims=True))
    return z / z.sum(axis=-1, keepdims=True)

def normalized_weights(labels, class_weights):
    """Dataset mean one, NEVER renormalize each one-example microbatch."""
    weights = np.asarray([class_weights[label] for label in labels], dtype=float)
    if not np.isfinite(weights).all() or (weights <= 0).any():
        raise ValueError('Strictly positive finite weights required')
    return weights / weights.mean()

def ideal_weighted_posterior(posterior, weights):
    """Population weighted-CE optimum q_y = w_y p_y / sum(w*p)."""
    p = np.asarray(posterior, dtype=float)
    w = np.asarray(weights, dtype=float)
    if p.shape != w.shape or (p < 0).any() or (w <= 0).any():
        raise ValueError('Invalid probability/weight vectors')
    return p*w / (p*w).sum()

def exact_legal_label_probabilities(token_log_probabilities):
    """Each list must include ALL JSON-answer tokens and the terminal EOS.

    Each label's conditional path must have been separately teacher-forced.
    Normalize the joint path likelihoods over these three legal sequences only;
    this is a restricted conditional distribution, not calibrated clinical risk.
    """
    if set(token_log_probabilities) != set(LABELS):
        raise ValueError('All three complete legal paths required')
    values = []
    for label in LABELS:
        path = np.asarray(token_log_probabilities[label], dtype=float)
        if path.ndim != 1 or not len(path) or not np.isfinite(path).all() or (path > 0).any():
            raise ValueError('Finite full-path log probabilities required')
        values.append(path.sum())
    return softmax(values)

def ce_loss_gradient(logits, target, weight=1.):
    q = softmax(logits)
    grad = q.copy();grad[target] -= 1
    return float(-weight*np.log(q[target])), weight*grad

def false_s_loss_gradient(logits, target, penalty=1.):
    """Illustrative exact-label risk, NOT enabled in selected 106 training.

    L = CE(y,q) + lambda * 1[y != S] * q(S).
    Class indexes are explicit. NS and NA do not receive a word-substring mask.
    This term specifically trades non-S -> S, unlike class-weighted CE; by
    itself it gives no preference between NS and NA. Autoregressive sequence
    likelihood gradients additionally require all three complete label paths.
    """
    loss, grad = ce_loss_gradient(logits, target)
    q = softmax(logits)
    if target != 0:
        dq = -q[0]*q;dq[0] += q[0]
        loss += penalty*q[0];grad += penalty*dq
    return float(loss), grad

def finite_difference(function, vector, eps=1e-6):
    vector = np.asarray(vector, dtype=float)
    out = np.zeros_like(vector)
    for i in range(len(vector)):
        left=vector.copy();right=vector.copy();left[i]-=eps;right[i]+=eps
        out[i]=(function(right)-function(left))/(2*eps)
    return out

def audit_token_objective():
    """Use actual tokenizer label lengths; arithmetic is not a model probe."""
    from collections import Counter
    import common106 as c
    audit=c.read(c.OUT/'tokenizer_labels.json')['labels']
    lengths={label:len(audit[label]['verdict_ids']) for label in LABELS}
    reports={}
    for name,counts in [('105_label196',{'Supported':83,'Not Supported':62,'Not Addressed':51}),
                        ('inactive_data_candidate512',{'Supported':320,'Not Supported':96,'Not Addressed':96})]:
        coef={label:counts[label]/lengths[label] for label in LABELS}
        reports[name]=dict(N=sum(counts.values()),counts=counts,
            direct_first_value_token_per_example={label:1/lengths[label] for label in LABELS},
            direct_first_value_token_coefficient_totals=coef,
            S_total=coef['Supported'],Not_total=coef['Not Supported']+coef['Not Addressed'],
            full_value_sequence_NLL_first_branch_S_total=counts['Supported'],
            full_value_sequence_NLL_first_branch_Not_total=counts['Not Supported']+counts['Not Addressed'],
            prior_only_illustration_not_9b_posterior={label:coef[label]/sum(coef.values()) for label in LABELS})
    result=dict(task=106,actual_verdict_value_lengths=lengths,
        other_answer_tokens={label:len(audit[label]['ids'])+1-lengths[label] for label in LABELS},
        current_mean_value_objective='per example (1/L_y)*sum value-token CE + mean other-answer CE',
        reports=reports,
        idealized_effect='If full legal value paths are independently optimizable, suffixes deterministic, and p(y|x) is nondegenerate, the value objective alone has q_y proportional to p_y/L_y.',
        strongest_counterexample='For perfectly separable one-hot conditional labels, all positive weights have the same zero-classification-error optimum. Coefficient totals pool different input contexts and do not reconstruct actual9B posteriors.',
        not_implementation_deviation='105 explicitly specified token mean and implementation matches it; this is an objective choice with a possible class-dependent bias, not a proven execution bug.',
        no_recovered_logits=True,no_GPU_or_model_probe=True,new_global_normalized_sum_prepared_not_GPU_executed=True,
        selected_candidate=dict(data='exact_original196',value_sum_divisor=360/196,
            per_value_token_coefficient=196/360,dataset_average_verdict_segment_total_weight=1,
            other_answer_mean_CE_coefficient=1,first_branch_S_total=83*196/360,first_branch_Not_total=(62+51)*196/360),
        decision='One minimal same196 objective diagnosis: frozen105 label_mean control versus fresh-original-base label_sum divided by fixed global360/196. Candidate512 data assets remain inactive. This is not a proven implementation bug or evidence-understanding improvement.')
    c.put(c.OUT/'tokenizer_objective_audit.json',result)
    print(c.canonical(result));return result

if __name__=='__main__':audit_token_objective()
