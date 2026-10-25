"""Update current entry points only, preserving each existing encoding/newline style."""
import re
import common095 as c

def update(path,fn):
    p=c.ROOT/path;raw=p.read_bytes();bom=raw.startswith(b'\xef\xbb\xbf');text=raw.decode('utf-8-sig' if bom else 'utf-8');nl='\r\n' if '\r\n' in text else '\n';plain=text.replace('\r\n','\n');new=fn(plain)
    if new==plain:return
    p.write_bytes((b'\xef\xbb\xbf' if bom else b'')+new.replace('\n',nl).encode('utf-8'))

def one(s,old,new):
    assert old in s,old[:80]
    return s.replace(old,new,1)

def main():
    assert (c.ROOT/'reviews/095_anchored_minimal_contrast/final_review.md').exists(),'final independent review must exist before current navigation announces closure'
    cov=c.read(c.OUT/'baseline_coverage.json');tab=c.read(c.OUT/'baseline_metrics.json')['common_core'];cost=c.read(c.OUT/'cost_ledger.json');a=tab['Original'];b=tab['B_PriorG'];fee=cost['total_directory_price_or_unknown_cny'];coverage=f"B成功覆盖{cov['successful_B']}/9065、共同core {cov['core_valid_B']}"
    result=f"{coverage}；同ID原作者/B＋G正确{a['correct']}/{b['correct']}、MCC {a['MCC']:.4f}/{b['MCC']:.4f}、false-S {a['false_S']}/{b['false_S']}。300构造、117核对后95自动拟触发，但语义核对失败，全局停止C最终Judge/扩量，不能称分类阴性；新增目录价及未知预留¥{fee:.6f}/150。"
    short=f"095已完成：{result}默认仍无示例B＋Frozen PriorG；本轮提交后停止，不自动096。"
    def agents(s):
        s=one(s,'# 项目工作约定（2026-09-27，094结项后）','# 项目工作约定（2026-09-28，095结项后）')
        s=one(s,'## 当前状态与数据授权\n\n','## 当前状态与数据授权\n\n- '+short+' [095报告](outputs/095_anchored_minimal_contrast/report.md) · [独立复核](reviews/095_anchored_minimal_contrast/final_review.md)。\n')
        s=s.replace('最新论文见[092完整稿](outputs/092_task_adapted_verifier/manuscript_zh.md)。','最新论文见[095完整稿](outputs/095_anchored_minimal_contrast/manuscript_zh.md)，092原稿保留。')
        s=one(s,'- 100名患者全部已有研究暴露。','- 095获用户明确授权使用全部100患者开展盘点、开发与评价；GT仅用于登记/评价，未进入构造、检索或Judge。095许可不自动授权后续研究，完整开发成绩不称独立测试。\n- 100名患者全部已有研究暴露。')
        return s
    update('AGENTS.md',agents)
    def readme(s):
        s=one(s,'当前已完成至 **094（2026-09-27）**','当前已完成至 **095（2026-09-28）**')
        s=one(s,'092完成100名患者9065条有效atomic claim的五折患者分组OOF。',result+'\n\n092完成100名患者9065条有效atomic claim的五折患者分组OOF。')
        s=one(s,'- [094正式报告]','- [095先读这个](outputs/095_anchored_minimal_contrast/report.md)、[统一9065结果](outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl)、[来源构造停止依据](outputs/095_anchored_minimal_contrast/candidate_cases.md)、[独立复核](reviews/095_anchored_minimal_contrast/final_review.md)\n- [094正式报告]')
        s=s.replace('[最新完整中文论文稿](outputs/092_task_adapted_verifier/manuscript_zh.md)','[最新完整中文论文稿](outputs/095_anchored_minimal_contrast/manuscript_zh.md)')
        s=s.replace('092又获明确授权','095也明确授权现有全部材料开展本轮开发/评价；092曾获明确授权',1)
        return s
    update('README.md',readme)
    def status(s):
        s=s.replace('# 项目现状（2026-09-27，094完成）','# 项目现状（2026-09-28，095完成）',1)
        s=one(s,'当前研究已完成至094；本轮起始HEAD 03a58bb3b','当前研究已完成至095；本轮起始HEAD 5ec748edd63be29d35fa920f10874aa158501ae5')
        marker='|094答案隔离'
        if marker not in s:
            # Table labels may include punctuation; insert before the actual first094 row.
            match=re.search(r'(?m)^\|094[^\n]*',s);assert match;marker=match.group(0)
        s=one(s,marker,f"|095统一基准/最小差异|{coverage}；原作者/B＋G正确{a['correct']}/{b['correct']}，MCC{a['MCC']:.4f}/{b['MCC']:.4f}|300构造数量通过但语义实施失败，未运行C分类；独立复核范围见报告，默认不变|\n"+marker)
        s=one(s,'[094报告]','[095总报告](../outputs/095_anchored_minimal_contrast/report.md) · [095独立复核](../reviews/095_anchored_minimal_contrast/final_review.md) · [094报告]')
        s=s.replace('[最新完整稿](../outputs/092_task_adapted_verifier/manuscript_zh.md)','[最新完整稿](../outputs/095_anchored_minimal_contrast/manuscript_zh.md)')
        s=s.replace('[研究问题与证据](../outputs/092_task_adapted_verifier/evidence_map.md)','[研究问题与证据](../outputs/095_anchored_minimal_contrast/evidence_map.md)')
        s=one(s,'094同样由用户授权使用既有全体材料',f'095经用户明确授权使用全部100患者，以9065为固定母体；{coverage}。构造95自动eligible不等于已部署，语义停止后未运行E/C。092两臂是原OOF，B/PriorG没有按其外层折重新拟合；均不称独立外部测试。\n\n094同样由用户授权使用既有全体材料')
        s=one(s,'094新增API ¥2.508135/20',f'095新增API目录价及未知预留¥{fee:.6f}/150，{cost["attempts"]}次尝试，{cost["HTTP200"]}个HTTP200；独立执行复核与自检分别留档，非独立医生审评。官方时段价对账不是账户退款或优惠扩额度。\n\n094新增API ¥2.508135/20')
        return s
    update('docs/PROJECT_STATUS.md',status)
    def index(s):
        s=s.replace('（截至094）','（截至095）',1).replace('[092完整论文](../outputs/092_task_adapted_verifier/manuscript_zh.md)','[095完整论文](../outputs/095_anchored_minimal_contrast/manuscript_zh.md)',1)
        return one(s,'|094_answer_isolated_verification|','|095_anchored_minimal_contrast|[总报告](../outputs/095_anchored_minimal_contrast/report.md)|[独立最终复核](../reviews/095_anchored_minimal_contrast/final_review.md)|统一9065母体B补齐与诊断；C构造语义失败，未运行分类，默认不变、不自动096|\n|094_answer_isolated_verification|')
    update('docs/TASK_INDEX.md',index)
    def policy(s):
        s=s.replace('（2026-09-27）','（2026-09-28）',1)
        s=one(s,'094已完成，新增API按未优惠原价累计¥2.508135/20',f'095已完成，专项总限150元，实际目录价及未知预留¥{fee:.6f}；094历史¥2.508135/20')
        s=one(s,'GPU实例的按小时租赁','095核实普通北京0731闲时22:00–08:00（UTC+8），输入/输出/缓存输入1.5/4.5/0.15元/百万token；忙时3/9/0.3。以官方当前目录价和实际usage核算，跨时段/未知保守保留，不把赠金、折扣券或余额当额度。新任务须重新核实适用模型/地域/时段；095源码和早期忙时估计快照都保留，历史其他任务费用不追溯改写。\n\nGPU实例的按小时租赁')
        s=s.replace('094使用现行阿里云路由完成授权实验','095使用现行阿里云路由完成授权B补齐与构造预检，最终E/C未运行')
        return s
    update('docs/API_POLICY.md',policy)
    update('docs/RESEARCH_EXECUTION.md',lambda s:one(s.replace('（2026-09-27）','（2026-09-28）',1),'当前094已完成','当前095已完成').replace('原20/40/40角色是历史元数据','095另获授权以全部9065母体盘点/开发/评价，构造语义停止不等于分类阴性。原20/40/40角色是历史元数据',1))
    def aliyun(s):
        s=s.replace('（2026-09-27）','（2026-09-28）',1)
        s=one(s,'092已完成，新增API0；没有待自动恢复的调用。',f'095已完成，新增目录价及未知预留¥{fee:.6f}/150；092历史新增API仍0。没有自动下一任务调用，095缺口/完整覆盖以其报告为准。')
        s=s.replace('加载器读取指定文件，进程启动时载入；运行中不会自动刷新key。','加载器调用时读取指定文件；已创建客户端不会自动刷新key。095在每个逻辑请求创建客户端，以冻结执行器为准，不应依赖修改通用默认来更改科学请求。')
        return s
    update('docs/aliyun/CURRENT.md',aliyun)
    def repro(s):
        s=s.replace('（2026-09-27）','（2026-09-28）',1)
        s=one(s,'092已完整结项；当前任务是文档同步，没有新研究、训练或收费调用。','095研究已结项，含B真实补齐、来源诊断与构造停止；本文是离线复查入口，不自动调用API或开启下一任务。')
        s=one(s,'## 优先只读\n\n','## 优先只读\n\n先看[095总报告](../outputs/095_anchored_minimal_contrast/report.md)、[统一9065表](../outputs/095_anchored_minimal_contrast/unified_9065_predictions.jsonl)和[最新稿](../outputs/095_anchored_minimal_contrast/manuscript_zh.md)。零API、无临床原文复算：\n\n```powershell\npwsh -NoProfile -File scripts/run_research.ps1 tasks/095_anchored_minimal_contrast/resume095.py verify-public\n```\n\n恢复B的准确入口、同一总账和成功不重发规则见[095 README](../tasks/095_anchored_minimal_contrast/README.md)；完成后恢复命令无新调用。\n\n')
        s=s.replace('日常查看[092报告]','092历史训练结果可查看[092报告]',1)
        return s
    update('docs/REPRODUCIBILITY.md',repro)
    def reviews(s):
        s=s.replace('（2026-09-27）','（2026-09-28）',1)
        s=one(s,'092已结项，执行者自检PASS，**独立审计未执行**。','095已完成独立执行者的缓存、构造来源、费用/恢复及最终指标复核，实际结论和范围见[095最终报告](095_anchored_minimal_contrast/final_review.md)，不是独立医生审评。092已结项，执行者自检PASS，**其独立审计仍未执行**。')
        return one(s,'|001_dataset_audit|','|095_anchored_minimal_contrast|[独立最终复核](095_anchored_minimal_contrast/final_review.md)；阶段缺口与修订记录保留|\n|001_dataset_audit|')
    update('reviews/README.md',reviews)
    print('Current navigation synchronized; historical reports, default and .gitignore untouched')
if __name__=='__main__':main()
