# 024 固定λ=2跨后端与跨模型迁移：发送前协议

登记日期：2026-09-19。用户授权总预算80元，研究范围为迁移验证；不调λ、不改prompt、不用reserved40。历史019–023结论保持。

## 科研目的与冻结条件

验证固定Supported偏置是否迁移到阿里云DeepSeek V4 Flash 0731，以及阿里云Qwen3.8-27B。复用020全部10名已暴露development患者879条valid atomic claims与API-BGE C48原文；保留原claim、reference内容及顺序。没有新检索/BGE请求。不能视为新的独立患者确认，也不能视为Qwen本地部署测试。

每模型一次普通structured B、一次019原版scoring S；一次S产生原始verdict V_raw、argmax U0、固定λ=2 U2。不要求两服务逐条复现历史结果。模型body仅替换model字符串；temperature=0、max_tokens=2048、enable_thinking=false、n=1、stream=false、原JSON schema。保留原始reason，不声称它解释后处理后的新标签。

决策复用019：log(max(score/100,1e-6))+λ·1[S]，平分优先NS、NA、S；只执行λ=0、2。三整数分数0..100且和100，沿用019严格解析。GT、author、患者ID、BHC不进入messages，仅claim/reference。完整患者队列是已冻结020材料；不重抽、不按新结果增减。

## 服务与预算

DeepSeek固定deepseek-v4-flash-0731；Qwen固定qwen3.8-27b（公开服务别名，尚无不可变权重证明）。记录实际回传model、request ID、usage、完整请求/响应。端点为本地.env.aliyun已配置北京兼容地址，密钥不保存到成果。

官方2026-09-19价格依据：DeepSeek快照忙时输入3/输出9元每百万token；Qwen输入3/输出12。均按无缓存原价保守计费，不混用通用DeepSeek别名1/2价格。来源见registry.json。按020 R0的1758次实际usage换算，两模型共3516次预计44.985315元，加30%余量58.4809095元。80元为任务累计硬上限，失败/未知预留同计，不按模型重置。成本为公开价估算，非账单。

每次发送前按UTF8请求字节数+2000作为保守输入token上界、最大输出2048预留；累计实际usage费用+未知及在途预留不得超过80元。如实际token增长致剩余预期总费超过80，暂停报告，不在看过新输出后缩队列。默认并发8，工程限流可减少并发/延时，但不得更改研究条件。先发送冻结清单中每模型/臂各首个请求共4个作为接口验证，成功输出即canonical；不用额外探测。

请求/回执逐尝试追加，发送前落盘reservation；HTTP200（包括非法/截断）不重跑，缺失/非法不补标签，不做available-case主评价。无回答失败至多另试两次，需保留旧失败及未知预留；遇服务错误先停并核查，不静默换模型。单任务锁、严格输入指纹核验。若返回模型不是指定ID则停。

## 分析与判断（新结果前冻结）

完成全3516合法输出才分析。002 evaluate/paired_compare；all micro为主，human/llm、每患者、三类别单列；1000次配对患者cluster bootstrap。主对比每模型U2−U0、U2−B；辅助V_raw−B、U0−V_raw、U2−V_raw。保留Always-S背景、混淆矩阵、S/NS/NA recall、false-S（分母真实non-S）、U0→U2的S rescue R、原正确non-S harm H、原错误non-S新false-S W。净正确=R−H；新增false-S=H+W，二者不可混淆。

迁移方向支持：U2对U0及B的总体PA和MCC点估计均正；强迁移证据进一步要求这四项配对95%区间下限均>0，并披露作者/患者及类别代价。区间跨0为不确定，不因为单一高PA宣称成功。两模型分别判断；跨模型一致性是收益—风险方向是否重复，不重新制定λ。作者和患者异质性完整披露；LLM Supported极多，不以PA单指标解释。相对020历史硅基流动同队列仅描述，非同期且版本不可完全对齐，不能把差异归因于供应商单一因素。

无论结果如何均停止024，交独立审计；不自动reserved test、不修改019–023、API路由或费用政策，不启动新方法。
