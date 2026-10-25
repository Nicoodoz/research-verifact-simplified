from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
entries=[
("README.md","# Research-VeriFact","""**041当前：** evidence-gated explanation synchronization已完成执行与自检。C48-only为83/342个U2翻转生成严格证据解释，R覆盖66/219=30.14%，H/W false-justification 17/123=13.82%；Expanded为153/342，R覆盖121/219=55.25%，但H/W false-justification升至32/123=26.02%。0 API，不选winner。 [041报告](outputs/041_evidence_gated_explanation_sync/report.md)。

**040当前：** 039结果落在预设规则未显式覆盖的混合区域：有效R中A66、B55、C94、D1；A+B=56.02%，但A<50%且B不超过A。零API，记录为mixed mechanism，041同时报告C48-only/Expanded选择性工作点。 [040报告](outputs/040_route_decision/report.md)。

**039当前：** 完整eligible EHR高召回归因已完成执行与自检。219条R中A66、B55、C94、D1、U3；121/219=55.25%可建立自动化完整支持，其中55条需C48外证据。H/W仍有32/123通过A+B，因此不能把自动证据审计直接当安全gate。924个HTTP200，约17.291343元；独立审计待进行。 [039报告](outputs/039_full_ehr_attribution/report.md)。
"""),
("docs/PROJECT_STATUS.md","# 项目现状总览","""**041当前：** 选择性证据门控解释同步已完成执行与自检。C48-only：83/342翻转有新解释，R66/219，H/W false-justification17/123；Expanded：153/342，R121/219，H/W false-justification32/123。扩大证据提高覆盖但没有提高有解释翻转的GT precision。0 API，不回写036方法。 [报告](../outputs/041_evidence_gated_explanation_sync/report.md)。

**040当前：** 有效R A/B/C/D=66/55/94/1；A+B=56.02%，但A<50%且B<=A，按事前规则无法归为单一主因，记录为mixed mechanism。0 API。 [报告](../outputs/040_route_decision/report.md)。

**039当前：** 342个U2翻转+120稳定对照完成目标住院完整eligible EHR高召回归因。R=219：A66、B55、C94、D1、U3；A+B=55.25%。H/W A+B=32/123。924个HTTP200，约17.291343元，独立审计待进行。 [报告](../outputs/039_full_ehr_attribution/report.md)。
""")
]
for rel,header,block in entries:
    p=ROOT/rel
    txt=p.read_text(encoding="utf-8")
    if block.splitlines()[0] in txt:
        print("already",rel);continue
    assert txt.startswith(header)
    pos=txt.find("\n",len(header))
    if pos<0:raise RuntimeError(rel)
    new=txt[:pos+1]+"\n"+block+"\n"+txt[pos+1:].lstrip("\r\n")
    p.write_text(new,encoding="utf-8")
    print("updated",rel)
