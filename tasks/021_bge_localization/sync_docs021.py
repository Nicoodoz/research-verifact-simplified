"""Byte-preserving sync of current navigation docs for task 021."""
from pathlib import Path
import json
import common021 as c

FILES=[c.ROOT/'README.md',c.ROOT/'docs/PROJECT_STATUS.md',c.ROOT/'docs/API_POLICY.md',c.ROOT/'AGENTS.md']
BACK=c.OUT/'documentation_sync_001'

P021_ROOT="**021 BGE本地化与冻结等价性检查完成（2026-09-19，尚未独立审计）。** 两个BGE模型已在RTX 3060 Laptop 6GB上完成本地化，并复用020冻结的10名development患者879条claim做全量API→本地等价性检查：固定API C48仅替换本地reranker时final reference完全一致594/879；embedding＋reranker全本地时565/879。事前严格门槛要求879/879，因此strict frozen equivalence=FAIL。本地实现可运行，但不能静默继承020 API-BGE的PA/MCC。021新增付费API为0、未使用reserved 40人、未用GT/Judge性能选实现。[021主报告](outputs/021_bge_localization/report.md)。"
P021_DOC="**021 BGE本地化与冻结等价性检查完成（2026-09-19，尚未独立审计）。** 两个BGE模型均已本地化；复用020冻结的879条claim检查后，固定API C48仅替换本地reranker的final reference完全一致594/879，embedding＋reranker全本地为565/879，未满足879/879严格冻结等价门槛。本地实现可运行，但020科学结果仍属于原API-BGE条件。0新付费API、reserved 40人未使用。[021主报告](../outputs/021_bge_localization/report.md)。"
P021_API="**021执行完成（2026-09-19，尚未独立审计）。** 021把BGE-M3 embedding与bge-reranker-v2-m3迁移到本地GPU，新增付费API调用为0。对020冻结879条claim的严格API→本地等价检查未通过（全本地final reference完全一致565/879），因此本地BGE不能被静默视为020 API-BGE的同一冻结实现；若后续使用本地BGE，应按新实现条件冻结并建立同期baseline。40名reserved test未使用。[021主报告](../outputs/021_bge_localization/report.md)。"
P021_AGENTS="**021 BGE本地化与冻结等价性检查完成（2026-09-19，尚未独立审计）。** BGE-M3与bge-reranker-v2-m3均已在RTX 3060 Laptop 6GB本地运行；复用020冻结879条claim，固定API C48仅换本地reranker时final reference完全一致594/879，embedding＋reranker全本地565/879，严格879/879等价门槛FAIL。021不改写020科学结果；若reserved test改用本地BGE，应把本地链路视作新实现条件并建立同期baseline。0新付费API，reserved 40人未使用。[021主报告](outputs/021_bge_localization/report.md)。"

def load_exact(path):
    return path.read_bytes().decode('utf-8')

def save_exact(path,text):
    path.write_bytes(text.encode('utf-8'))

def dominant_sep(text):
    crlf=text.count('\r\n')
    lf=text.count('\n')
    return '\r\n' if crlf and crlf>=lf/2 else '\n'

def insert_after_title(text,paragraph):
    if paragraph in text:
        return text
    sep=dominant_sep(text)
    first_end=text.find(sep)
    if first_end<0:
        raise ValueError('no first newline')
    pos=first_end+len(sep)
    if text.startswith(sep,pos):
        pos+=len(sep)
    return text[:pos]+paragraph+sep+sep+text[pos:]

def insert_row_after(text,marker,row):
    if row in text:
        return text
    sep=dominant_sep(text)
    pos=text.find(marker)
    if pos<0:
        raise ValueError('missing table marker '+marker)
    end=text.find(sep,pos)
    if end<0:
        end=len(text)
        return text+sep+row
    end+=len(sep)
    return text[:end]+row+sep+text[end:]

def patch_readme(text):
    text=insert_after_title(text,P021_ROOT)
    old=next((x.rstrip('\r') for x in text.split('\n') if x.rstrip('\r').startswith('当前阶段：020已完成固定λ=2')),None)
    if old:
        text=text.replace(old,'当前阶段：021已完成两个BGE的本地化与API→本地冻结等价性检查；严格等价门槛FAIL，因此020的科学结果仍属于原API-BGE实现条件，不能自动继承到本地链路。001–018已有相应独立审计依据；019、020、021尚未独立审计。40名development均已用于开发/确认；021仅复用020冻结development输入，40名reserved test继续保留，是否开启最终测试及采用API还是本地BGE需另行冻结决策。',1)
    row='| '+chr(96)+'021_bge_localization'+chr(96)+' | 两个BGE本地化完成；严格API→本地冻结等价FAIL，尚未独立审计 | [任务](tasks/021_bge_localization/README.md) · [中文主报告](outputs/021_bge_localization/report.md) · [当前状态](outputs/021_bge_localization/CURRENT.md) |'
    text=insert_row_after(text,chr(124)+' '+chr(96)+'020_lambda2_patient_validation'+chr(96)+' '+chr(124),row)
    text=text.replace('当前研究状态以020本段、[项目现状总览]','当前研究状态以021本段、020科学结果段、[项目现状总览]',1)
    text=text.replace('截至2026-09-16，**001–018均已完成并有相应独立审计依据**。','截至2026-09-19，**001–018均已完成并有相应独立审计依据；019、020、021已完成执行/分析但尚未独立审计**。',1)
    text=text.replace('40名reserved test仍未用于方法选择或020评价。','021仅复用020冻结development输入；40名reserved test仍未用于方法选择或020/021评价。',1)
    return text

def patch_status(text):
    text=insert_after_title(text,P021_DOC)
    text=text.replace('当前状态以本页020段、020主报告及最新独立审计为准','当前状态以本页021段、020科学结果段、对应主报告及最新独立审计为准',1)
    text=text.replace('更新：2026-09-18。','更新：2026-09-19。',1)
    if '**021当前：**' not in text:
        sep=dominant_sep(text)
        text=text.replace('**020当前：**','**021当前：** 两个BGE模型已本地化并完成879条claim的冻结结构对照；严格879/879 final evidence等价门槛未通过。020的PA/MCC仍只属于原API-BGE条件。021没有新API、没有reserved test、没有按GT/Judge性能调实现。[021主报告](../outputs/021_bge_localization/report.md) · [交审材料](../outputs/021_bge_localization/audit_handoff.md)。'+sep+sep+'**020当前：**',1)
    text=text.replace('019与020已完成执行/分析但尚未独立审计','019、020与021已完成执行/分析但尚未独立审计',1)
    text=insert_row_after(text,'| 020 |','| 021 | 两个BGE本地化完成；API→本地严格冻结等价FAIL（全本地reference 565/879 exact）；尚未独立审计 |')
    text=text.replace('40名reserved test仍未用于020或方法选择。001/002已有全体汇总','021仅复用020冻结development输入；40名reserved test仍未用于020/021方法选择或评价。001/002已有全体汇总',1)
    text=text.replace('是否开启最终测试需在020独立审计和方法冻结后另行决定。','是否开启最终测试需在019–021独立审计及最终实现（API BGE或本地BGE）冻结后另行决定。',1)
    return text

def patch_api(text):
    text=insert_after_title(text,P021_API)
    text=text.replace('当前API执行状态以020本段及最新服务路由登记为准','当前API执行状态以021本段、020历史执行段及最新服务路由登记为准',1)
    text=text.replace('本页仅记录现行规则；020已按独立80元任务登记并完成真实调用','本页仅记录现行规则；021为0新API的本地化任务，020已按独立80元任务登记并完成真实调用',1)
    return text

def patch_agents(text):
    text=insert_after_title(text,P021_AGENTS)
    text=text.replace('当前状态以020本段、docs/PROJECT_STATUS.md及最新独立审计为准','当前状态以021本段、020科学结果段、docs/PROJECT_STATUS.md及最新独立审计为准',1)
    if '021已完成两个BGE的本地化与API→本地冻结等价检查' not in text:
        sep=dominant_sep(text)
        text=text.replace('020已完成固定λ=2','021已完成两个BGE的本地化与API→本地冻结等价检查，尚未独立审计。[021主报告](outputs/021_bge_localization/report.md)为当前工程结果入口。严格879/879 final evidence等价门槛FAIL，因此本地BGE不是020 API-BGE的静默替代；若未来reserved test使用本地BGE，必须把它作为新实现条件冻结并建立同期baseline。021未使用GT/Judge性能选实现，0新付费API，reserved test未使用。'+sep+sep+'020已完成固定λ=2',1)
    text=text.replace('截至2026-09-18，001–018均完成并有相应独立审计依据；019和020完成执行/分析但尚未独立审计。','截至2026-09-19，001–018均完成并有相应独立审计依据；019、020和021完成执行/分析但尚未独立审计。',1)
    text=text.replace('40名reserved test仍不用于方法选择。009形成的C48仍是实用证据baseline；','021仅复用020冻结development输入；40名reserved test仍不用于方法选择。009形成的C48仍是实用证据baseline；',1)
    text=text.replace('历史负结果不换名重跑，后续若进入最终测试必须先冻结方法与评价。','历史负结果不换名重跑；后续若进入最终测试，必须先冻结方法、评价以及API BGE或本地BGE的实现选择。',1)
    return text

def main():
    funcs={FILES[0]:patch_readme,FILES[1]:patch_status,FILES[2]:patch_api,FILES[3]:patch_agents}
    changes={}
    for p in FILES:
        before=(BACK/p.relative_to(c.ROOT)).read_bytes()
        old=load_exact(p)
        new=funcs[p](old)
        save_exact(p,new)
        rel=p.relative_to(c.ROOT)
        changes[rel.as_posix()]={'before_sha256':c.sha256(BACK/rel),'after_sha256':c.sha256(p),'changed':before!=p.read_bytes(),'separator':'CRLF' if dominant_sep(old)=='\r\n' else 'LF'}
    c.save(BACK/'changes.json',changes)
    print(json.dumps(changes,ensure_ascii=False),flush=True)

if __name__=='__main__':
    main()
