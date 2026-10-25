"""Documentation-only current-state sync; preserve every frozen result/code/audit."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/documentation_sync/20260916_001'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8',newline='\n') as f:json.dump(obj,f,ensure_ascii=False,indent=2);f.write('\n')
def edit(name,fn):
    p=ROOT/name;raw=p.read_bytes();newline='\r\n' if b'\r\n' in raw else '\n'
    text=raw.decode('utf-8').replace('\r\n','\n');new=fn(text)
    assert new!=text,name
    p.write_bytes(new.replace('\n',newline).encode('utf-8'))

def main():
    assert not OUT.exists(),'Sync already recorded'
    OUT.mkdir(parents=True)
    tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    before={n:sha(ROOT/n) for n in tracked if n and (ROOT/n).is_file()}
    save(OUT/'before.json',dict(HEAD=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),tracked_sha256=before))
    def agents(t):
        start=t.index('## 当前研究状态');end=t.index('已完成 `001_dataset_audit`',start)
        t=t[:start]+'''## 当前研究状态

截至2026-09-16，001–016均完成并有相应独立审计依据。016已快速独立审计PASS，可冻结／结项；这是成果可复查性通过，不是方法通过。其review在601条上正确452条，较Qwen457条净−5、较普通repeat451条净+1，未达原门槛，停止该方向，不做v2/v3或剩余患者确认。当前唯一必读[016主报告](outputs/016_disagreement_triggered_review_validation/completion_002/report.md)，独立依据见[016审计](reviews/016_disagreement_triggered_review_validation.md)。

003固定20名探索、40名开发、40名reserved test。前30名开发患者已使用，剩余10名继续保留；reserved test不用于方法选择。009形成的C48仍是实用证据baseline，未证明最优；014/016支持保留Qwen作为较小模型研究对象，但未证明普遍优越、非劣或本地部署性能。013具体四路线、015双候选仲裁和016当前分歧复核均停止；历史负结果不换名重跑。最终论文方法与贡献仍待论证。

现行API约定：V4-Flash先用硅基流动启用号池，Qwen继续用阿里云；硅基流动所有启用账号明确额度耗尽后，通知用户，后续所有API工作转阿里云。新任务预计累计费用≤80元可直接执行，超过80元或无法合理估算时先确认；跨账号、供应商、阶段累计。细则见下方费用规则及[API现行约定](docs/API_POLICY.md)。本次授权不重启已结项实验。

阅读顺序：[现状总览](docs/PROJECT_STATUS.md) → 根README任务表 → 各任务正式主报告与审计末尾。冻结README、旧current_result、报告及交审快照中的“当前／待审／暂停”仅代表形成时状态，不覆盖现行总览。下方001–013分节中的队列余量、费用和下一步建议均按其历史阶段理解。

'''+t[end:]
        start=t.index('## API 调用费用与确认规则');end=t.index('\n---',start)
        t=t[:start]+'''## API 调用费用与确认规则

- 最新长期授权（用户2026-09-16）：一次新任务／实验预计收费API总费用不超过人民币80元（含80元），可直接执行；超过80元或无法合理估算时，说明用途、预计总费和上限后先取得确认。默认费用保护上限80元，用户另行指定的具体上限优先。每次发送不得让累计费用及在途预留超过有效上限。
- 按完整任务累计，包括收费预检、重试／补跑、所有模型、账号、供应商和阶段，以及未知请求的费用预留；换号、切平台、暂停、重启或拆批均不重置额度。发送前登记范围、实时价格依据、预估和上限，不把≤80元的正常登记变成逐次询问。
- V4-Flash优先硅基流动：从`.env.siliconflow_pool`启用的`SILICONFLOW_API_KEY_2`开始，明确余额不足后按`_3`、`_4`等编号顺序切换。已停用`_1`不重新启用、不重编号。此前充值90元是历史用户记录，不是当前余额。
- Qwen目前继续阿里云。硅基流动所有启用账号的额度均明确耗尽后，必须告知用户，并将后续所有API调用工作转到阿里云，包括DeepSeek、Qwen以及其他模型／API服务；不中途重发已成功回答。切换已获本条授权，不因切换本身再次询问。
- 耗尽依据为真实调用的明确无答案余额错误及完整号池台账；超时、503、限流、鉴权错误或缺少key都不等于额度耗尽。触发全平台迁移后保存持久记录（账号别名、耗尽回执、时间、通知及目的平台），后续任务直接沿用阿里云，不重新试已耗尽号池，除非用户另行指示。当前尚无全部耗尽的证据，不作无意义余额／key探测。
- 阿里云密钥在`.env.aliyun`；硅基流动密钥在`.env.siliconflow_pool`，不输出或提交key。平台切换须登记模型ID、端点、生成设置、价格及供应商限制，不能声称同名模型等价。若阿里云没有可核实的对应服务，报告具体缺项，不静默替换检索／模型条件或回到已耗尽平台。
- 本规则取代未来任务原40元长期门槛。已冻结001–016的授权、预算、回执和代码保留当时记录（016历史上限40元、最终21.79039103元），不追溯改成80元、不复用旧授权启动新实验。旧执行器的40元保护不改写；新任务在独立登记和执行器中采用80元规则。已有成功回答、失败和未知预留必须保留。
- 新执行器如需授权文件，可引用本条长期授权并记录估算，不能虚构逐次批准。现行入口与自动化实现边界见[API_POLICY.md](docs/API_POLICY.md)及[阿里云当前说明](docs/aliyun/CURRENT.md)。
'''+t[end:]
        # Current future-facing references only; historical task caps/numbers stay unchanged.
        for old,new in [('任务预估总费用不超过 40 元可直接执行','任务预估总费用不超过 80 元可直接执行'),
                        ('不超过 40 元无需再次确认','不超过 80 元无需再次确认'),
                        ('当前 API 40 元长期费用授权规则继续适用','当前 API 80 元长期费用授权规则适用于新任务'),
                        ('用户最新长期授权为任务预估总费用 ≤40 元直接执行','用户最新长期授权为新任务预估总费用 ≤80 元直接执行')]:t=t.replace(old,new)
        start=t.index('## 014当前执行边界')
        t=t[:start]+'''## 014–016已审成果与停止边界

- **014固定证据模型比较**：旧6名开发患者650条，C48和structured固定，Qwen与已有010 V4比较，非同期。Qwen整体接近，human NA召回弱于V4；不能宣称非劣、本地性能或普遍最优。历史预算40元、累计10.761264元；修订定向独立复核PASS，R1/R2关闭。[正式报告](outputs/014_qwen27b_baseline_comparison/report.md) · [审计](reviews/014_qwen27b_baseline_comparison.md)。
- **015双候选理由仲裁**：同旧650条中78条分歧，主方案523/650，低于最强单模型527；无候选evidence_only对照542只是探索信号，不事后改为winner。主方案停止，历史40元上限、usage估算2.0524446元；修订复核PASS。候选顺序偏差保留。[正式报告](outputs/015_disagreement_adjudication/report.md) · [审计](reviews/015_disagreement_adjudication.md)。
- **016新患者复现**：开发序25–30的6人601条，V4/Qwen完整，92条分歧各跑普通repeat及015原版review。正确数446/457/451/452，原发布系统489；review较最强单模型−5、较repeat+1，gate=false。human NA和患者损失保护条件亦未全部满足，停止本方向。快速独立审计PASS，未作剩余10名确认。历史总上限40元、已知估算19.37526542元＋未知预留2.41512561元＝21.79039103元。[正式报告](outputs/016_disagreement_triggered_review_validation/completion_002/report.md) · [审计](reviews/016_disagreement_triggered_review_validation.md)。
- 016 Qwen保留127条硅基流动＋474条阿里云回答，基础模型跨时段；仅是本实际流程的验证，不能作严格同期单供应商因果结论。旧服务暂停、V4补齐、供应商测试、失败与停止锁全部保留历史字节，旧待审措辞不代表当前状态。
- 正常顶层导航更新与不可变计算材料分开。历史run、嵌套报告、审计原文、冻结源码、输入、回执和指标严格校验；用户最新预算／路由指示适用于未来任务，不改写历史manifest。没有新实验或付费探测的自动待办。
'''
        return t
    edit('AGENTS.md',agents)
    def readme(t):
        start=t.index('\n\n')+2;end=t.index('基于 VeriFact-BHC',start)
        t=t[:start]+'''截至2026-09-16，**001–016均已完成并有相应独立审计依据**。016快速独立审计PASS，可冻结／结项；其方法没有通过事前门槛：601条上V4/Qwen/repeat/review正确数446/457/451/452，review较最强单模型−5、较repeat+1，停止当前方向。当前唯一必读[016中文主报告](outputs/016_disagreement_triggered_review_validation/completion_002/report.md)；[独立审计](reviews/016_disagreement_triggered_review_validation.md)。

患者沿003固定20/40/40分组：前30名开发患者已使用，剩余10名保留，40名reserved test不用于方法选择。C48仍是实用证据baseline，未证明最优；Qwen可保留为较小模型研究对象，未证明普遍优越或本地部署性能。013四路线、015仲裁和016当前复核均停止，最终论文方法及贡献仍待论证。

**最新调用约定：** V4先用硅基流动启用号池，Qwen继续阿里云；硅基流动号池额度全部明确耗尽后通知用户，后续所有API工作转阿里云。新任务预计总费≤80元可直接执行，超过80元或无法合理估算时先确认；跨模型、账号、供应商累计。历史实验预算保持原值，016为¥21.79039103／¥40，不自动重启。

阅读入口：[项目现状总览](docs/PROJECT_STATUS.md) · [API现行约定](docs/API_POLICY.md) · [任务表](#5-current-status) · [审计索引](reviews/README.md)。冻结README、旧current_result和历史报告中的“当前／暂停／待审”仅代表当时版本；后续以这些现行入口与审计末尾为准。

'''+t[end:]
        old='当前阶段：001–015执行及相应独立审计均已完成，014/015复现修订已通过定向复核。014是固定证据模型比较，015无winner并停止；011 main、013组合及015新患者确认均未启动。保留C48实用对照、统一评价和患者划分；最终方法及论文贡献仍未确定。'
        t=t.replace(old,'当前阶段：001–016执行与相应独立审计均已完成。014/015修订阻塞已关闭；016新患者验证未达门槛并停止。未开展016后续冻结确认；前30名开发已使用，剩余10名保留。历史负结果、C48、002统一评价和003分组保持，最终论文方法与贡献仍待论证。')
        t=t.replace('tasks/016_disagreement_triggered_review_validation/current_result.md','tasks/016_disagreement_triggered_review_validation/CURRENT.md')
        t=t.replace('当前环境支撑001–013的数据处理、评价和服务调用','当前环境支撑001–016的数据处理、评价和硅基流动／阿里云服务调用')
        t=t.replace('一次任务预估总费用不超过 40 元可直接执行','一次新任务预估总费用不超过 80 元可直接执行')
        start=t.index('## 11.');end=t.index('\n## 12.',start)
        t=t[:start]+'''## 11. API账号、平台与费用（现行）

执行前读取[API_POLICY.md](docs/API_POLICY.md)和[AGENTS费用规则](AGENTS.md#api-调用费用与确认规则)。新任务默认80元累计保护；≤80元直接执行，超过或无法合理估算先确认，跨模型、账号、供应商、阶段和重试累计。

V4-Flash先使用硅基流动启用号池，从account_2起按编号换号；Qwen继续阿里云。所有启用硅基流动账号明确额度耗尽后，通知用户并永久记录此次转换，后续全部API工作转阿里云，除非用户另有指示。超时／503不当作额度耗尽，目前未确认全部耗尽。

本地密钥位置：`.env.siliconflow_pool`与`.env.aliyun`，现有.gitignore已排除，勿提交或打印。配置与实现边界见[硅基流动说明](docs/siliconflow_pool/README.md)、[阿里云当前说明](docs/aliyun/CURRENT.md)。单次工具、历史runner和研究任务的冻结预算须区分；旧016的40元硬保护及全部回答不改写，新任务另行登记80元上限。此次同步不调用API、不查询余额、不重新启动历史任务。

以下第12–23节回顾各任务形成时的发现与建议，不是新的执行授权；当前状态以顶部总览和审计索引为准。
'''+t[end:]
        t=t.replace('40名开发仍只使用前24名，剩余16名及40名reserved test不用于本轮','011当时40名开发只使用前24名，剩余16名及40名reserved test未用于011')
        t=t.replace('剩余16名development与40名reserved test不动','013当时剩余16名development与40名reserved test未用于013')
        t+='''
## 21. 014固定证据模型比较（修订独立复核PASS）

旧6名开发患者650条，同C48和structured，Qwen与010已有V4比较；两者非同期。Qwen可保留为较小模型研究对象，但human NA较弱，未证明非劣或本地部署性能。见[主报告](outputs/014_qwen27b_baseline_comparison/report.md)及[审计](reviews/014_qwen27b_baseline_comparison.md)。

## 22. 015双候选理由仲裁（修订独立复核PASS，停止）

主仲裁523/650，比最强单模型527净−4；evidence_only对照542只是探索性正向信号，后由016验证。015没有winner，不追加v2/v3；候选顺序偏差保留。见[主报告](outputs/015_disagreement_adjudication/report.md)及[审计](reviews/015_disagreement_adjudication.md)。

## 23. 016分歧触发独立复核（独立审计PASS，停止）

新6名开发患者601条，92条分歧；review452，低于Qwen457，只比普通repeat451多1条。原继续门槛未通过，human NA及患者保护亦有损失；停止当前方向，不以局部MCC提升挽救。未使用余下10名开发患者或reserved test确认。Qwen混合供应商、基础模型跨时段，限制保留。见[当前成果入口](outputs/016_disagreement_triggered_review_validation/CURRENT.md)、[主报告](outputs/016_disagreement_triggered_review_validation/completion_002/report.md)及[审计](reviews/016_disagreement_triggered_review_validation.md)。
'''
        return t
    edit('README.md',readme)
    def reviews(t):
        t=t.replace('001–013均有相应独立审计记录，013未筛出可扩大方案','001–016均有相应独立审计记录，013、015、016均没有可自动扩大的winner')
        return t.replace('未来收费规则见[AGENTS]','未来API路由与80元总额规则见[现行约定](../docs/API_POLICY.md)及[AGENTS]')
    edit('reviews/README.md',reviews)
    def pool(t):
        start=t.index('\n\n')+2;end=t.index('\n\n',start)
        t=t[:start]+'''现行约定（2026-09-16）：V4-Flash先用硅基流动启用号池，从`SILICONFLOW_API_KEY_2`开始，明确余额不足后依次`_3`、`_4`等；停用`_1`不启用、不重编号。Qwen继续阿里云。号池所有启用账号明确额度耗尽后，必须通知用户，后续所有API工作转阿里云并持久记录，不自动回切。新任务预计累计费用≤80元可直接执行，超过80元或无法合理估算先确认；历史实验的40/16/8元上限不改写。详见[API现行约定](../API_POLICY.md)。此前充值90元是历史记录，不代表余额；本次不查询余额或测试key。'''+t[end:]
        t=t.replace('SILICONFLOW_API_KEY_1=第一个账号的key','# SILICONFLOW_API_KEY_1=已停用，保留本地原值，不启用')
        t=t.replace('当前账号确有 16 元可用额度','当前账号的可用额度')
        t=t.replace('当前账号余额。','当前账号余额。最近016的硅基流动调用来自account_2；尚无全号池耗尽证据。',1)
        t=t.replace('不能将阶段上限相加当新授权','不能将阶段上限相加当新授权；后续新任务采用80元现行门槛，历史40元记录不变')
        t=t.replace('所有账号耗尽时暂停并保留进度。可在原列表末尾追加更大编号的新账号，再恢复；','这个旧通用Runner在所有账号耗尽时暂停并保留进度；它本身没有跨平台调度器。按最新约定，执行者须通知用户并登记切到阿里云，不默认等待充值。只有用户明确要求恢复硅基流动时，才在原列表末尾追加账号并恢复；')
        t=t.replace('当前API费用规则处理','当前API费用规则处理')
        t=t.replace('按用户最新长期授权，一次任务预估 API 总费用不超过 40 元（含 40 元）','按用户2026-09-16最新长期授权，一次新任务预估 API 总费用不超过 80 元（含 80 元）')
        t=t.replace('超过 40 元或无法合理估算时先确认','超过 80 元或无法合理估算时先确认')
        t=t.replace('默认时自动执行上限设为 40 元','默认时自动执行上限设为 80 元').replace('无另行指定预算时自动执行上限设为 40 元','无另行指定预算时自动执行上限设为 80 元')
        t=t.replace('费用按整个任务跨账号累计','费用按整个任务跨账号、供应商和阶段累计')
        t=t.replace('新任务／阶段可能重新从第一个账号尝试，目前没有全项目永久停用开关','旧Runner自身没有全项目永久停用开关；新任务须先读取并遵守全平台迁移登记，不能因此重新尝试已耗尽号池')
        return t
    edit('docs/siliconflow_pool/README.md',pool)
    changed={n for n,h in before.items() if sha(ROOT/n)!=h}
    expected={'README.md','AGENTS.md','reviews/README.md','docs/siliconflow_pool/README.md'}
    assert changed==expected,changed
    save(OUT/'changes.json',[dict(path=n,before_sha256=before[n],after_sha256=sha(ROOT/n)) for n in sorted(changed)])
    print(json.dumps(dict(updated=sorted(changed),base_head='4703e84',new_api_calls=0),ensure_ascii=False))

if __name__=='__main__':main()
