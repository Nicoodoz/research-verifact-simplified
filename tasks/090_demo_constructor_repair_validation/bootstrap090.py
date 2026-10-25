"""Task-local reuse of already tested I/O/API/evaluation, never edit historical sources."""
from pathlib import Path
root=Path(__file__).resolve().parents[2];task=Path(__file__).parent
for name in ('common','api','analyze'):
    s=(root/'tasks/089_source_audited_demo_compression'/f'{name}089.py').read_text(encoding='utf-8-sig')
    s=s.replace('089_source_audited_demo_compression','090_demo_constructor_repair_validation').replace('089','090')
    if name=='common':
        s=s.replace("OUT=ROOT/'outputs/090_demo_constructor_repair_validation'","PUB=ROOT/'outputs/090_demo_constructor_repair_validation'\nOUT=ROOT/'outputs/replays/090_demo_constructor_repair_validation'")
        s=s.replace("ARMS=('F4','P4','Q4')","ARMS=('B','F4','P90','Q90')").replace('CAP=20.','CAP=40.')
    if name=='api':
        s=s.replace('cap_cny=20','cap_cny=40').replace('limit=20','limit=40').replace('limit<=20','limit<=40').replace('<=20+1e-9','<=40+1e-9').replace('workers=1,limit=2','workers=1,limit=4').replace("assert f['cap']==20","assert f['cap']==40")
    if name=='analyze':
        s=s.replace("PAIRS=(('F4','P4'),('Q4','P4'),('F4','Q4'))","PAIRS=(('F4','P90'),('Q90','P90'),('B','F4'),('B','P90'),('B','Q90'),('F4','Q90'))")
        s=s.replace("jobs=api.validate_main();", "global ARMS,PAIRS\n    ARMS=tuple(read(OUT/'templates.json')['active_arms']);PAIRS=tuple((b,c) for b,c in PAIRS if b in ARMS and c in ARMS)\n    jobs=api.validate_main();")
        s=s.replace('cap=20','cap=40').replace("<=20 and construction<=2","<=40 and construction<=4").replace("natural/P4-F4/PriorG/MCC","natural/P90-F4/PriorG/MCC (only if P90 usable)")
    with (task/f'{name}090.py').open('x',encoding='utf-8',newline='\n') as f:f.write(s)
(task/'.gitattributes').write_text('* -text\n',encoding='utf-8')
