# 094 固定C48答案隔离式问答核验

[中文报告](../../outputs/094_answer_isolated_verification/report.md) · [完整指标](../../outputs/094_answer_isolated_verification/detailed_tables.md) · [历史区别](../../outputs/094_answer_isolated_verification/history_difference.md) · [病例](../../outputs/094_answer_isolated_verification/case_analysis.md)

32条冻结队列，自然20、机制富集12；B原默认、V答案可见问答、Q答案隔离问答。问题经执行者GT盲语义检查26条可用，其余复用同期B，不换样本。记录问题限定和空白来源定位两处工程修正，原生成/取证成功回执不重发。主判断前冻结唯一版本，不继续搜索。

## 复查

CPU/API环境research-verifact-029。零API复查：

```powershell
pwsh -NoProfile -File scripts/run_research.ps1 tasks/094_answer_isolated_verification/test094.py
pwsh -NoProfile -File scripts/run_research.ps1 tasks/094_answer_isolated_verification/verify094.py
```

完整源数据/回执需要合法的本地私有目录.local_models/094，以及原092/历史评估输入；公开ID/哈希/指标不能替代私有病历。inspect_content094会显示临床内容，仅限本地，不上传日志。

执行链为prepare→freeze→preflight→generate→questions→review_questions→build_extract→extract→extraction→align_sources→build_judge→judge→analyze。api094是历史执行器，不代表新调用授权；已有成功请求跳过，不启动任何新版本。报告和分析另存，独占写入保护历史结果；重新生成整套结果应在隔离副本中进行，不删除当前结果来绕过保护。

design_freeze/runner_freeze/judge_freeze分别绑定初始设计、发送器及最终流程。extraction_quality为初版严格定位，extraction_quality_aligned为只修正空白后的实际记录；比较使用后者。content_review是不看GT和最终成绩的执行者内容描述，不是新gold或独立审计。最终结论以report和decision为准，默认B始终不改。
