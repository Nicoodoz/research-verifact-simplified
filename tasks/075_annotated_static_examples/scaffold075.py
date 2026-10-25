"""Create isolated 075 execution files, without modifying historic tasks."""
from pathlib import Path
R=Path(__file__).resolve().parents[2];T=Path(__file__).parent
def write(name,text):
 with (T/name).open('x',encoding='utf-8',newline='\n') as f:f.write(text)
def main():
 c=(R/'tasks/074_anchor_dynamic_examples/common074.py').read_text(encoding='utf-8-sig').replace('074 shared IO','075 shared IO').replace('outputs/074_anchor_dynamic_examples','outputs/075_annotated_static_examples')
 write('common075.py',c)
 r=(R/'tasks/074_anchor_dynamic_examples/run074.py').read_text(encoding='utf-8-sig').replace('bounded 074 executor','bounded 075 executor').replace('outputs/074_anchor_dynamic_examples','outputs/075_annotated_static_examples').replace('FROZEN_BEFORE_074_API','FROZEN_BEFORE_075_API')
 assert 'deepseek-v4-flash-0731' in r
 write('run075.py',r)
 a=(R/'tasks/074_anchor_dynamic_examples/analyze074.py').read_text(encoding='utf-8-sig').replace('frozen 074 stages','frozen 075 stages').replace('run074','run075').replace('outputs/074_anchor_dynamic_examples','outputs/075_annotated_static_examples')
 start=a.index('    final_pairs["H6_minus_F6"]');end=a.index('    core_valid =',start)
 a=a[:start]+a[end:]
 a=a.replace('[("F4","B"),("F6","F4"),("H6","B"),("H6","F4"),("H6","F6")]','[("F4","B"),("R4","B"),("R4","F4")]')
 a=a.replace('    metrics = {arm: metric(rows, maps[arm]) for arm in arms}','    metrics = {arm: metric(rows, maps[arm]) for arm in arms}')
 write('analyze075.py',a)
 test=(R/'tasks/074_anchor_dynamic_examples/test_transport074.py').read_text(encoding='utf-8-sig').replace('run074','run075').replace('outputs/074_anchor_dynamic_examples','outputs/075_annotated_static_examples').replace("prefix='074_transport_'","prefix='075_transport_'")
 write('test_transport075.py',test)
 print('075 scaffold prepared; no API')
if __name__=='__main__':main()
