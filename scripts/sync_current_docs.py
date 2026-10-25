"""2026-09-15 documentation-only synchronization from existing independent audits."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/documentation_sync/20260915_001'
changes=[]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def edit(name,replacements,reason,notice=None):
    path=ROOT/name
    raw=path.read_bytes()
    nl='\r\n' if b'\r\n' in raw else '\n'
    text=raw.decode('utf-8').replace('\r\n','\n')
    for before,after in replacements:
        assert before in text,(name,before)
        text=text.replace(before,after)
    if notice:
        title,rest=text.split('\n',1)
        text=title+'\n\n'+notice+'\n'+rest
    updated=text.replace('\n',nl).encode('utf-8')
    assert updated!=raw,name
    path.write_bytes(updated)
    changes.append(dict(file=name,reason=reason,before_sha256=hashlib.sha256(raw).hexdigest(),after_sha256=sha(path),line_endings=repr(nl)))

def main():
    OUT.mkdir(parents=True,exist_ok=False)
    names=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0')
    # Tracked files only: no credential files or ignored clinical data are read here.
    assert not any(n.startswith('.env') for n in names if n)
    tracked={n:sha(ROOT/n) for n in names if n and (ROOT/n).is_file()}
    write_json(OUT/'before.json',dict(head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        origin_main=subprocess.check_output(['git','rev-parse','origin/main'],cwd=ROOT,text=True).strip(),
        status=subprocess.check_output(['git','status','--short'],cwd=ROOT,text=True),tracked_sha256=tracked))

    notice='截至2026-09-15，001–009执行均已完成并有相应独立审计依据；009重放修订定向复核PASS，原阻塞关闭，可正式冻结／结项。当前暂用C48、保留A48对照；优先单独验证EHR证据组织／打包中的检查身份、事件时间和实施状态，尚未证明其改进有效或确立论文主线。暂缓通用planner扩展、纯dense替代、融合公式网格与无限扩容。003的40名开发患者已有前24名用于方法／案例分析，剩余16名沿原顺序使用；40名reserved test不用于方法选择。详见[009成果入口](outputs/009_retrieval_baselines/README.md)及[独立审计末尾](reviews/009_retrieval_baselines.md)。'
    edit('README.md',[
        ('当前已完成：','任务编号示例（完整当前状态见第5节）：'),
        ('## 15. Retrieval Baselines and Evidence Loss','## 16. Retrieval Baselines and Evidence Loss'),
        ('首个假设已完成 004 小规模 pilot，第二个实验未执行；003 的观察仍不是已经验证的方法贡献。','首个假设已完成004 pilot；003原第二个实验未按原方案单独执行，相关证据利用问题已在005–009继续分析，不是当前自动待办。003观察仍非已验证的方法贡献。'),
        ('下一步推荐是在未逐例分析的两名开发患者上，比较普通 structured 与加入局部来源上下文的 structured，固定 claim/reference 和原医生标签，来源文本只作理解辅助，不当 EHR 证据。','005当时推荐的两患者来源上下文实验已由006完成；其后续方向以009为准。'),
    ] if '下一步推荐是在未逐例分析的两名开发患者上，比较普通 structured 与加入局部来源上下文的 structured，固定 claim/reference 和原医生标签，来源文本只作理解辅助，不当 EHR 证据。' in (ROOT/'README.md').read_text(encoding='utf-8') else [
        ('当前已完成：','任务编号示例（完整当前状态见第5节）：'),
        ('## 15. Retrieval Baselines and Evidence Loss','## 16. Retrieval Baselines and Evidence Loss'),
        ('首个假设已完成 004 小规模 pilot，第二个实验未执行；003 的观察仍不是已经验证的方法贡献。','首个假设已完成004 pilot；003原第二个实验未按原方案单独执行，相关证据利用问题已在005–009继续分析，不是当前自动待办。003观察仍非已验证的方法贡献。')],
        '前置009当前统一状态、说明早期假设不是新待办、去掉不完整的已完成列表语义、修正重复章节号',notice)

    edit('AGENTS.md',[
        ('## 当前研究状态','## 当前研究状态\n\n'+notice.replace('(outputs/','(outputs/')),
        ('- baseline 默认采用正文 R1-70B + 100 sentence facts、rerank、absolute_time、current admission、deduplicate=True。','- 002发布预测的历史参照baseline采用正文R1-70B + 100 sentence facts、rerank、absolute_time、current admission、deduplicate=True；这不是当前新实验的默认检索链路。009后的暂定实用baseline为C48＋BGE rerank＋DeepSeek-V4-Flash structured，A48保留同期对照，不能将两个不同阶段/模型的绝对分数直接当优化收益。'),
        ('40 名开发患者可用于下一步验证与调参','冻结40名开发患者中，前24名已用于方法/案例分析，剩余16名可沿原哈希顺序用于后续确认；规则开发优先复用已使用患者'),
        ('003 提出的候选小实验优先考察','003当时提出的候选小实验优先考察'),
        ('- 当前建议修改切入点，先离线确认 EHR 片段与原记录/事件时间能否可靠连接，再考虑固定命题、同证据预算的新对照；本轮未启动此后续实验。','- 006当时建议修改切入点、先核对EHR片段来源；后续007–009已完成本地原文索引、原claim重排与候选对照。当前优先级见009，不能把006的准备建议当尚未开展的总任务。'),
        ('- 当前建议有针对性验证“来源补充候选、原 claim 约束证据重排”，先修正零预算/无关头部截取并完善基本召回；尚未确定论文主线，也未启动下一实验。','- 007当时建议“来源补充候选、原claim约束重排”；008–009已执行相关受控对照，并采用独立固定上限、完整段打包及事前body缓存。新问题是语义身份/时间/状态仍可能被切开；当前优先级见009，原007缺陷和成绩不回写。'),
        ('优先候选融合、证据覆盖/组织和 Judge 支持边界，暂不扩大通用 planner；','这是008当时对后续检查的建议，009已完成基础融合对照；当前优先证据组织与Judge支持边界，暂缓通用planner、融合公式网格和无限扩容；'),
    ],'消除顶层停留004、历史R1与当前C48混称、开发余量和006–008旧待办的歧义')

    edit('reviews/README.md',[
        ('| 记录 | 原审计及后续状态 | 当前使用 |','| 记录 | 原审计及后续状态 | 成果用途与限制 |'),
        ('可接受为已完成的探索性分析，进入下一方案设计；上下文收益与创新性仍待验证','已完成的探索性依据；当时上下文建议的后续验证见006，当前优先级见009'),
        ('可结项；局部召回信号不等于稳定净收益，扩大前先修正预算截取和完善对照','可结项；局部召回不等于稳定收益，当时预算/截取控制的后续处理见008–009'),
        ('可结项；尚无稳定 planner 优势，继续前先处理接口损耗和候选融合／证据选择','可结项；尚无稳定planner优势，009已作空白解析诊断和基础检索对照，当前方向见009'),
    ],'保留所有独立结论，仅让索引用途不把早期下一步建议当当前待办',
    '阅读顺序：各审计末尾最新追加决定当前状态，不能用009文件开头的初审／有条件通过措辞覆盖末尾修订PASS。早期审计里的后续建议与预算是当时记录；当前研究方向见[009成果入口](../outputs/009_retrieval_baselines/README.md)，未来收费规则见[AGENTS](../AGENTS.md#api-调用费用与确认规则)。')

    edit('tasks/002_reproduce_paper_results/README.md',[
        ('| baseline | 每个已发布配置分别重评分 | 正文 R1-70B、sentence facts N100、rerank、absolute_time、current admission、deduplicate=True |','| 发布预测的历史参照baseline | 每个已发布配置分别重评分 | 正文 R1-70B、sentence facts N100、rerank、absolute_time、current admission、deduplicate=True |'),
    ],'区分002历史发布预测参照与009当前可部署比较链路',
    '本页固定002复算与长期评价口径；R1-70B是发布预测的历史参照。当前新实验暂用C48并保留A48对照，见[009入口](../../outputs/009_retrieval_baselines/README.md)。评价实现仍用002，不能把不同任务或模型的绝对分数当同期收益。')
    edit('outputs/002_reproduce_paper_results/README.md',[
        ('## 后续采用的 baseline','## 发布预测的历史参照 baseline 与统一评价'),
        ('默认配置是 R1-70B','本页历史参照配置是 R1-70B'),
    ],'移除R1为一切后续实验默认的歧义',
    '当前新实验的暂定实用链路见[009入口](../009_retrieval_baselines/README.md)：C48、保留A48对照；本页保留002的发布预测及全benchmark统计，不替代同期开发比较。')
    edit('tasks/003_error_analysis/README.md',[
        ('第二个小实验尚未执行，两个假设均不是已确定的论文贡献。','原第二个小实验未按003原方案单独执行；相关证据利用问题已由005–009继续检验，不是当前自动待办。两个假设均不是已确定的论文贡献。'),
    ],'标明原第二假设的历史位置，更新分组使用余量',
    '003的20/40/40分组保持不变。至009，开发组前24名已用于方法/案例分析，剩余16名沿原顺序使用；当前建议以[009已审结论](../../outputs/009_retrieval_baselines/README.md)为准。')
    edit('outputs/003_error_analysis/README.md',[
        ('第二个小实验尚未执行。','原第二个小实验未按003原方案单独执行；相关问题已在005–009继续分析，不是当前自动待办。'),
    ],'保留003假设与患者划分，避免旧待办和40名全未用的误读',
    '本页描述003当时的探索工作。至009，40名开发患者中的前24名已用于方法/案例分析，剩余16名；保留测试不用于方法选择。当前研究优先级见[009入口](../009_retrieval_baselines/README.md)。')

    labels={'005_pilot_effect_analysis':'005','006_source_context_feasibility':'006','007_context_retrieval':'007','008_retrieval_planning':'008'}
    for dirname,number in labels.items():
        audit=f'../../reviews/{dirname}.md'
        status=f'已通过2026-09-14'+('独立审计' if number=='005' else '精简独立审计')+f'，无阻塞修正；依据见[审计记录]({audit})。'
        history='原主报告、交审清单、自查记录以及报告源稿中的“等待审计”保留形成时状态；以本入口和审计最新结论判断任务状态。后续研究优先级以[009入口](../../outputs/009_retrieval_baselines/README.md)为准，旧建议不是新的待执行授权。'
        replacements=[]
        if number=='005':
            replacements=[('2026-09-14 执行分析及自查完成，等待独立审计。',status),('下一步建议是先验证','005当时建议先验证'),('这项后续实验在 005 形成时尚未执行；','该候选已由006检验，仍未证明净收益；')]
        elif number=='006':
            replacements=[('当前为执行分析完成、等待独立复核。',status)]
        elif number=='007':
            replacements=[('**执行分析与自查完成，等待独立复核。**','**'+status+'**'),('低于长期授权的 16 元。','低于本任务当时授权的16元（未来任务长期规则为40元，不回写本轮预算）。'),('当前建议有针对性修改召回/证据组织，并验证原 claim 约束的重排','007当时建议修改召回/证据组织并验证原claim约束重排；相关对照已由008–009执行')]
        edit(f'tasks/{dirname}/README.md',replacements,f'{number}任务入口同步已有独立审计并区分原方案与当前方向',
            (status+' ' if number=='008' else '')+history+' tasks目录中的report.md/report_template.md及research_notes是本任务报告源稿或定向阅读底稿，不是滚动更新的项目状态页。')
        output_history='原主报告及交审／自查文件保留当时状态，当前完成状态以本入口和审计为准。后续研究见[009入口](../009_retrieval_baselines/README.md)，不自动重新执行原“下一步”建议。'
        if number=='005':
            replacements=[('**执行分析与自查完成，等待独立审计。**','**'+status+'**'),('主要发现与下一步推荐以主报告为准','本任务的发现与当时推荐以主报告为准，当前方向见009')]
        elif number=='006':
            replacements=[('**当前：执行分析完成，等待独立复核。**','**'+status+'**')]
        elif number=='007':
            replacements=[('**当前：执行分析与自查完成，等待独立复核。只需优先阅读','**'+status+'只需优先阅读'),('当前自查不是独立审计 PASS。','自查与独立审计分别记录；当前独立结论见上方审计链接。')]
        else:
            replacements=[('**执行分析与自查完成，等待独立复核。优先只读','**'+status+'优先只读'),('建议先研究候选融合与证据覆盖/组织，暂不扩大当前版本。','008当时建议检查候选融合与证据组织；009已完成基础对照，目前优先证据组织，暂缓扩大通用planner。'),('准确基准 HEAD 与未提交成果见交审清单；当前状态不等于独立审计 PASS。','当时基准HEAD及未提交成果见历史交审清单；当前独立状态见上方审计记录。')]
        edit(f'outputs/{dirname}/README.md',replacements,f'{number}成果入口消除等待审计旧状态，明确报告历史措辞',output_history)

    edit('outputs/009_retrieval_baselines/README.md',[
        ('|复核版本|[交审入口](audit_handoff.md)；[精确文件清单](handoff_001.json)|','|当前独立结论／修订被审版本|[审计末尾修订PASS](../../reviews/009_retrieval_baselines.md)；[revision_001清单（当时被审快照）](revision_001/handoff.json)|\n|首次交审历史|[旧交审入口](audit_handoff.md)；[handoff_001历史清单](handoff_001.json)|'),
        ('|验证|[143项断网测试与逐字节重放](verification_001/verification.json)、[完整测试日志](verification_001/tests.log)|','|当前修订验证|[146项断网测试／109文件重放](revision_001/verification_001/verification.json)；[测试日志](revision_001/verification_001/tests.log)|\n|首次验证历史|[143项测试](verification_001/verification.json)|'),
        ('上表handoff_001为历史首次交审版本。','上表handoff_001为历史首次交审版本，revision_001清单也只表示当时被审字节，不要求以后正常入口／审计追加仍与它一致。'),
    ],'使009首选链接直达修订PASS与146项验证，明确旧报告/交审历史性',
    '状态阅读提示：report.md、paper_draft.md、audit_handoff.md和revision_001/README.md保留执行／交审时原文；其中“等待独立复核”、143项测试及旧HEAD不是当前状态。009审计开头和中段也保留初审历史，当前以其末尾2026-09-15修订PASS为准。研究数值与限制不变。')

    edit('docs/siliconflow_pool/README.md',[
        ('本次只进行了虚构回执离线测试，没有调用推理 API；真实服务下的多账号切换尚未实测。','工具初次交付时仅做虚构离线测试。其后009已保存account_1无答案402后转account_2成功的真实记录，见[009已审结果](../../outputs/009_retrieval_baselines/README.md)。这不代表已验证所有错误恢复路径或当前账号余额。'),
        ('已创建空白文件；每行一个不同账号的 key','这是本地凭据文件，本文不声明其当前是否为空；每行一个不同账号的 key'),
        ('后续符合 [当前 API 费用规则](../../AGENTS.md#api-调用费用与确认规则) 的实验由新的','下列运行命令、固定预算预留和遇429暂停的行为专指通用多账号Runner。006–009复用账号读取功能，但另有各任务的计费/重试执行器；009的有界暂时错误重试、usage结算及固定阶段额度以其冻结协议和native_stage.py为准，不能混用恢复命令。后续符合[当前API费用规则](../../AGENTS.md#api-调用费用与确认规则)的任务可按已登记方案使用通用'),
        ('已标记耗尽的账号不会因重启自动重新启用。','同一运行状态里已标记耗尽的账号不会因恢复自动启用；新任务／阶段可能重新从第一个账号尝试，目前没有全项目永久停用开关。新增key在下次启动/恢复时加载，运行进程不会即时重读。'),
    ],'用009真实换号记录替换未实测旧说法，区分通用Runner与任务执行器及跨任务账号状态')
    write_json(OUT/'changes.json',changes)
    print(json.dumps(dict(modified_documents=len(changes),files=[x['file'] for x in changes]),ensure_ascii=False))

def finish_edits():
    global changes
    changes=json.loads((OUT/'changes.json').read_text(encoding='utf-8'))
    old_reasons={x['file']:x['reason'] for x in changes}
    edit('README.md',[
        ('## 12. Pilot Effect Analysis','以下第12–15节回顾各任务形成时的发现与建议，不是当前待办；下一步统一以第16节及顶部009状态为准。\n\n## 12. Pilot Effect Analysis'),
        ('建议优先验证局部来源上下文与 EHR 证据的角色区分，尚未确立方法收益或论文贡献。','005当时建议验证局部来源上下文与EHR证据的角色区分，006已完成该验证且未证明净收益；不作为新的待执行实验。'),
        ('当前环境覆盖 001–004 的数据处理、评价和服务调用','当前环境支撑001–009的数据处理、评价和服务调用'),
        ('当前暂用C48、保留A48对照；','当前暂用C48、保留A48对照，尚未证明C48稳定优越或非劣；'),
    ],'补充逐任务段落的历史性质，清除005旧待办并明确C48限制')
    edit('AGENTS.md',[
        ('当前暂用C48、保留A48对照；','当前暂用C48、保留A48对照，尚未证明C48稳定优越或非劣；'),
        ('具体模型元信息、实际队列与结果以 002 为准。','发布预测元信息及全benchmark队列以002为准；新实验实际模型、队列与结果以该任务冻结协议为准。'),
    ],'明确C48非稳定优越，以及002元信息不统辖后续模型和队列')
    edit('docs/动态切分提示词.md',[],
         '防止直接阅读旧Hospital-02材料时把其当前模型、Stage09和动态切分路线套到Research-VeriFact',
         '**历史项目材料：本文的“当前项目／正式版本／Stage 09”均指此前Hospital-02项目及文中标注日期，不是Research-VeriFact的009或后续待办。** 保留原技术记录供参考；不能把其动态切分结果、模型设置或建议当作本项目已验证结论。Research-VeriFact当前状态与暂定C48链路见[009入口](../outputs/009_retrieval_baselines/README.md)。')
    before=json.loads((OUT/'before.json').read_text(encoding='utf-8'))['tracked_sha256']
    merged={}
    for item in changes:
        name=item['file']
        reason=old_reasons.get(name,'')
        if reason and reason!=item['reason']:
            reason+='；'+item['reason']
        else:
            reason=item['reason']
        merged[name]=dict(item,before_sha256=before[name],after_sha256=sha(ROOT/name),reason=reason)
    write_json(OUT/'changes.json',list(merged.values()))
    print('Final documentation edits:',len(merged))

if __name__=='__main__':
    import sys
    finish_edits() if '--finish' in sys.argv else main()
