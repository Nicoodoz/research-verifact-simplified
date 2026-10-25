"""Create the final 020 report after complete inference and fixed analysis. No API calls."""
from pathlib import Path
from collections import Counter
import json
import common020 as c

def pct(x): return f"{100*x:.2f}%"
def f4(x): return f"{x:.4f}"
def ci(x):
    a,b=x
    return f"[{a:+.4f}, {b:+.4f}]"

def run():
    a=c.OUT/'analysis_001'
    c.require((c.OUT/'inference_complete.json').exists(),'Inference not complete')
    c.require(a.exists(),'Run analyze020 first')
    metrics=c.read(a/'metrics.json'); paired=c.read(a/'paired.json'); decision=c.read(a/'decision.json')
    stability=c.csvrows(a/'stability.csv'); norm=c.jsonlines(a/'normalized.jsonl')
    ledger=c.read(c.OUT/'live_ledger.json')
    rows=[]
    for rep in range(2):
        for author in ('all','llm','human'):
            for arm in ('B','U0','U2','O'):
                m=metrics[f'r{rep}/{author}/{arm}']
                rows.append((rep,author,arm,m))
    lines=['# 020：固定 λ=2 的新患者双轮验证','',
      '执行日期：2026-09-18。**020已完成推理与冻结分析；本报告不是独立审计PASS。**','',
      '## 结论先行','']
    out=decision['outcome']['all']
    if out['B']['joint_positive']:
        lines.append('**固定 λ=2 在剩余10名development患者上，两轮相对同期B的PA和MCC方向均为正，复现了019开发信号。**')
    else:
        lines.append('**固定 λ=2 未在剩余10名development患者上稳定复现“两轮PA和MCC均提高”的预注册方向。**')
    lines += ['', '## 1. 冻结范围', '',
      '- 10名剩余development患者，879条valid atomic claims；reserved test未使用。',
      '- 019后固定λ=2，不搜索新阈值；C48、rerank、Judge提示词与三分类定义保持。',
      '- B和评分版各两轮，共3516个Judge逻辑请求；两轮分别评价，不合并成独立样本。',
      '- 原VeriFact O只作同ID历史发布系统对照，不是同期同后端纯模型对照。','',
      '## 2. 主要结果','',
      '|轮次|范围|方法|PA|MCC|AC1|false-S|',
      '|---:|---|---|---:|---:|---:|---:|']
    for rep,author,arm,m in rows:
        lines.append(f"|R{rep}|{author}|{arm}|{pct(m['percent_agreement'])}|{f4(m['mcc'])}|{f4(m['gwet_ac1'])}|{m['counts']['false_s']}|")
    lines += ['', '## 3. U2相对B的配对变化','',
      '|轮次|范围|ΔPA|PA 95% CI|ΔMCC|MCC 95% CI|',
      '|---:|---|---:|---|---:|---|']
    for rep in range(2):
        for author in ('all','llm','human'):
            p=paired[f'r{rep}/{author}/U2-minus-B']['metrics']
            lines.append(f"|R{rep}|{author}|{p['percent_agreement']['delta']:+.4f}|{ci(p['percent_agreement']['ci95'])}|{p['mcc']['delta']:+.4f}|{ci(p['mcc']['ci95'])}|")
    lines += ['', '## 4. U2相对原VeriFact O','',
      '|轮次|范围|ΔPA|PA 95% CI|ΔMCC|MCC 95% CI|',
      '|---:|---|---:|---|---:|---|']
    for rep in range(2):
        for author in ('all','llm','human'):
            p=paired[f'r{rep}/{author}/U2-minus-O']['metrics']
            lines.append(f"|R{rep}|{author}|{p['percent_agreement']['delta']:+.4f}|{ci(p['percent_agreement']['ci95'])}|{p['mcc']['delta']:+.4f}|{ci(p['mcc']['ci95'])}|")
    flips={k:sum(str(r[k]).lower()=='true' for r in stability) for k in ('B_flip','V_raw_flip','U0_flip','U2_flip')}
    stable_rescue=sum(str(r['stable_rescue']).lower()=='true' for r in stability)
    stable_harm=sum(str(r['stable_harm']).lower()=='true' for r in stability)
    providers=Counter((r['provider'],r['account']) for r in norm)
    lines += ['', '## 5. 重复稳定性与执行', '',
      f"- 两轮标签翻转：B {flips['B_flip']}，V_raw {flips['V_raw_flip']}，U0 {flips['U0_flip']}，U2 {flips['U2_flip']}。",
      f"- 两轮都从B错误救回为U2正确：{stable_rescue}条；两轮都从B正确变为U2错误：{stable_harm}条。",
      f"- 任务累计费用/未知预留：{ledger['used_or_reserved_cny']:.6f}元 / 80元上限。",
      '- 成功Judge回答供应商分布：' + '；'.join(f"{p}/{a}: {n}" for (p,a),n in sorted(providers.items())) + '。','',
      '## 6. 解释边界','',
      '- 020验证的是019后固定的λ=2候选，不倒改019原“低false-S”门槛失败结论。',
      '- U2是对评分的离线决策调整；它不会自动重写原reason，因此分类指标改善不等于解释已可部署。',
      '- 新10名患者未参与019阈值选择，但001/002做过全体汇总，因此不称“任何层面从未接触”。',
      '- 本轮仍是development确认；40名reserved test没有被用于方法选择或本轮评价。',
      '- 本报告为执行者自查结果，需独立审计后再冻结任务状态。','']
    (c.OUT/'report.md').write_text('\n'.join(lines),encoding='utf-8')
    summary=dict(created_utc=c.now(),status='analysis_complete_pending_independent_audit',
      claims=879,rounds=2,fixed_lambda=2,reserved_test_used=False,
      outcome=decision['outcome'],label_flips=flips,stable_rescue=stable_rescue,stable_harm=stable_harm,
      used_or_reserved_cny=ledger['used_or_reserved_cny'],
      providers={f'{p}/{a}':n for (p,a),n in providers.items()},
      core_replaced=False,independent_audit=False)
    c.write_json(c.OUT/'run_summary.json',summary)
    print(c.canonical(summary))

if __name__=='__main__': run()
