"""Record training-only microbatch change; preserve original cache binding and freeze."""
from pathlib import Path
import common092 as c
cfg=c.read(c.TASK/'config.json');current=(c.TASK/'config.json').read_text(encoding='utf-8');old=current.replace('"window_microbatch":8','"window_microbatch":2')
binding=c.read(Path(cfg['activation_cache'])/'binding.json');assert c.digest(old)==binding['config_sha']
c.put(c.OUT/'cache_config_compatibility.json',dict(old_config_sha=binding['config_sha'],current_config_sha=c.sha(c.TASK/'config.json'),only_changed_field='window_microbatch',unused_by_cache_forward=True,old_value=2,new_value=8,cache_window_tokenization_and_backbone_unchanged=True,formal_training_started=False,reason='Training window batch changed after synthetic memory preflight while cache tokenization had already bound initial config; no classification outcome used.',utc=c.now()))
