"""Read the new reason field without changing the existing label parser.

Structural checks do not establish clinical correctness, sentence count,
faithfulness to the reference, or consistency of the reason and verdict.
"""
import json
from pathlib import Path
import re
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'105_brief_supervision'))
from parse105 import parse as parse_label


def inspect_output(content, finish_reason='stop', require_reason=False):
    label = parse_label(content, finish_reason)
    result = dict(classification=label, reason_present=False, reason_is_nonempty_text=False,
                  reason_structure_valid=False, reason=None,
                  semantic_review_required=True, sentence_count_verified=False,
                  label_rewritten=False)
    value = None
    if label['valid'] and not label['exact_label_normalized']:
        text = content.strip()
        fenced = re.fullmatch(r'\s*```(?:json)?\s*\n(.*?)\n```\s*', content, re.S|re.I)
        # parse_label has already rejected duplicate keys and malformed JSON.
        value = json.loads(fenced[1] if fenced else text)
    if isinstance(value, dict) and 'reason' in value:
        result['reason_present'] = True
        reason = value['reason']
        result['reason_is_nonempty_text'] = isinstance(reason, str) and bool(reason.strip())
        if result['reason_is_nonempty_text']:
            result['reason'] = reason
    result['reason_structure_valid'] = bool(label['valid'] and (
        result['reason_is_nonempty_text'] if require_reason or result['reason_present'] else True))
    return result
