"""GPU label arms share this pre-GPU frozen parser; strict JSON also retained."""
from parse103 import parse_content,LABELS
def parse_label(content,finish=None):
 strict=parse_content(content,finish)
 if strict['valid']:return dict(strict,strict_json_valid=True,exact_label_normalized=False)
 if isinstance(content,str) and content.strip() in LABELS:
  return dict(verdict=content.strip(),valid=True,finish_reason=finish,strict_json_valid=False,exact_label_normalized=True,format_anomaly=True)
 return dict(strict,strict_json_valid=False,exact_label_normalized=False)
