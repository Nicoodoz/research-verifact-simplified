"""Small deterministic text features; arguments contain no GT or patient identity."""
import math,re
WORDS=re.compile(r"[a-z]+(?:'[a-z]+)?|\d+(?:\.\d+)?")
STOP={'the','a','an','of','to','in','on','at','for','and','or','with','was','were','is','are','be','been','being','patient','he','she','his','her','it','as','by','from','that','this','had','has','have'}
TEMPORAL=re.compile(r'\b(?:before|after|during|initially|subsequently|later|prior|recent|admission|discharge|postoperative|day|days|week|weeks)\b',re.I)
CAUSAL=re.compile(r'\b(?:because|due to|secondary to|as a result|caused by|related to|in response to)\b',re.I)
CHANGE=re.compile(r'\b(?:increas\w*|decreas\w*|improv\w*|resolv\w*|continu\w*|remain\w*|versus|multiple|twice|times|chang\w*)\b',re.I)
NEGATION=re.compile(r'\b(?:no|not|without|never|denied|negative|absent)\b',re.I)
CONJUNCTION=re.compile(r'\b(?:and|or|but|with|while|whereas)\b',re.I)
FEATURE_NAMES=('native_margin','log_claim_words','numeric_count','negation_count','temporal_count','causal_count','change_comparison_count','conjunction_count','content_word_reference_coverage')

def features(claim,reference,native_margin):
    if not isinstance(claim,str) or not isinstance(reference,str) or not math.isfinite(native_margin):raise ValueError('Actual claim/reference and finite native margin required')
    words=WORDS.findall(claim.lower());content={w for w in words if w not in STOP and not w[0].isdigit()}
    reference_words=set(WORDS.findall(reference.lower()))
    coverage=len(content&reference_words)/len(content) if content else 0.
    return [float(native_margin),math.log1p(len(words)),float(len(re.findall(r'\d+(?:\.\d+)?',claim))),float(len(NEGATION.findall(claim))),float(len(TEMPORAL.findall(claim))),float(len(CAUSAL.findall(claim))),float(len(CHANGE.findall(claim))),float(len(CONJUNCTION.findall(claim))),coverage]
