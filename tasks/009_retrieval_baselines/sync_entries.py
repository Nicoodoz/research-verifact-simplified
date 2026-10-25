"""Update only current entry documents, retaining their original newline encoding."""
import study009 as s


def edit(path,operation):
    raw=path.read_bytes()
    assert not raw.startswith(b'\xef\xbb\xbf')
    newline='\r\n' if b'\r\n' in raw else '\n'
    text=raw.decode('utf-8').replace('\r\n','\n')
    updated=operation(text)
    path.write_bytes(updated.replace('\n',newline).encode('utf-8'))


def root_readme(text):
    old='008 已完成 LLM 检索规划验证与自查，等待独立复核，尚无稳定净收益，优先研究候选融合与证据组织。'
    new='008 已通过精简独立审计（见 reviews/008）；009 已完成检索基线比较、650条新开发命题确认、证据干预和离线自查，等待独立复核。C48暂作实用baseline，尚未证明稳定优势；下一步优先证据组织与Judge支持边界。'
    assert old in text
    text=text.replace(old,new)
    old='| `008_retrieval_planning` | 执行分析与自查完成，等待独立复核 |'
    assert old in text
    text=text.replace(old,'| `008_retrieval_planning` | 已通过精简独立审计（2026-09-14；见 reviews/008） |')
    row='| `009_retrieval_baselines` | 执行与离线自查完成，等待独立复核 | [任务说明](tasks/009_retrieval_baselines/README.md) · [简明中文主报告](outputs/009_retrieval_baselines/report.md) |'
    marker='| `008_retrieval_planning`'
    end=text.index('\n',text.index(marker))
    text=text[:end]+'\n'+row+text[end:]
    text+='\n## 15. Retrieval Baselines and Evidence Loss\n\n009先用008旧患者开发，再冻结A48（BM25+dense RRF）、B48（dense）和C48（两路交替保留48候选），在原开发顺序第19–24名患者全部650条valid claim确认。三臂共享原claim重排、Judge与证据上限，均完整。C−A的LLM/human ΔMCC为+0.0002/+0.0158，未证明稳定优势；B在人写组净少判对20条。证据损失同时出现于候选门槛、每note限制、字符容量和Judge解释，优先验证完整证据组织，暂缓扩大通用planner。全任务usage估算¥18.0822＜¥40；143项断网测试、原回执重放通过。阅读[唯一主报告](outputs/009_retrieval_baselines/report.md)及[交审入口](outputs/009_retrieval_baselines/audit_handoff.md)，自查不等于独立审计。008当前独立结论以[审计记录](reviews/008_retrieval_planning.md)为准，历史报告保留原状态。\n'
    return text


def agents(text):
    old='008_retrieval_planning 已完成执行与自查，等待独立复核；'
    assert old in text
    text=text.replace(old,'008_retrieval_planning 已通过2026-09-14精简独立审计（范围见 [reviews/008](reviews/008_retrieval_planning.md)）；')
    marker='## 之前的研究经验'
    section='''## 009 当前成果与后续边界

- 009_retrieval_baselines 已完成执行、真实确认、证据干预及离线自查，等待独立复核；唯一必读[主报告](outputs/009_retrieval_baselines/report.md)，设置/结果/相关工作草稿另存。执行者不宣布独立审计PASS，不改原独立意见。
- 开发复用008的144条；确认使用冻结开发哈希顺序第19–24名59250、93640、15057、27036、59840、66218的全部650条valid claim（LLM243，human407），方案在新结果前冻结。前24名开发患者已用于方法/案例分析，剩余16名仍按原顺序使用；reserved test未用于本轮。
- 主比较A48=BM25＋BGE-M3 dense RRF，B48=dense；C48=两路交替加入未见ID、保留48候选。共用本地原EHR索引、原claim BGE rerank、DeepSeek-V4-Flash structured、每note2/最多16整段/正文与记录头8000字符；来源不进入最终claim或Judge。
- 三臂各650条预测完整。B−A的LLM/human ΔMCC为+0.0205/−0.0526；C−A为+0.0002/+0.0158，患者区间均跨0。C暂作成本/复杂度相近的实用baseline，A保留参照；未证稳定优势或非劣性，不能包装成新方法贡献。
- 全量链路诊断＋旧15例/新35例完整阅读＋9例补回/移除/背景/重复干预。N302支持局部治疗段影响标签；MRI身份/结果分离、同note限额、候选前截取与Judge范围/NS-NA边界并存。锚点非医学gold，正确标签不保证证据理解正确。新确认预设重复1/12翻转，困难诊断重复5/18翻转，原答案不替换。
- 本任务总上限40元，全部阶段usage估算¥18.08218167（非账单），2692逻辑任务/2700HTTP尝试，含8个402无答案后切账号。无付费预检、新planner或失败补标签。开发重排漂移后统一刷新登记在execution_amendment_001.md；dev_embed槽实际为rerank，已计入总费，历史答案保持不变。
- Planner仅做旧输出的空白校验修正（128通过、16仍退回），作为新开发条件保留，未重评其效果。暂缓扩大通用planner、纯dense替代及无边界融合/容量搜索；下一步优先在已使用开发患者上单独验证EHR身份/局部原文组织，再冻结后确认，不能用新患者反复调参。
- 143项断网测试通过，原文/向量/排名/真实分数/打包/完整body缓存可重建，评分与案例渲染逐字节一致。日常重放不锁根README/AGENTS/审计文档；冻结材料/回执继续校验。可复用baseline配置与接口见tasks/009_retrieval_baselines；实际交审HEAD、未提交文件与指纹见[交审入口](outputs/009_retrieval_baselines/audit_handoff.md)，审计期间停止改动。

---

'''
    assert marker in text and '## 009 当前成果' not in text
    return text.replace(marker,section+marker)


if __name__=='__main__':
    edit(s.ROOT/'README.md',root_readme)
    edit(s.ROOT/'AGENTS.md',agents)
    print('Only current README/AGENTS entries updated; historical runs/reviews unchanged')
