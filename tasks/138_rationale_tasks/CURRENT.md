# 138 rationale_tasks：性能诊断已启动

响应用户性能优先要求：133已安全暂停，不再补完。本任务复用120 final369和127已有36条训练理由，以独立理由任务辅助156条标签任务；两轮384次呈现、固定48步。匹配label_replay对照的数据、原始ID曝光和更新数已冻结，主臂出现有用信号才运行。

评价使用136完全相同的claim_repeat、160个ID、完整reference与384输出上限。无新reason生成、无教师改标、无评价训练、无后接分类器。主臂已启动，实时训练和评价进度见进度文件；尚无分类成绩。

仍按09:36:01起新增20元GPU/原80元API累计，不关机、不释放。预计主臂含回传35–55分钟；后续只按真实性能决定。

[方案](PROTOCOL.md) · [准备统计](../../outputs/138_rationale_tasks/preparation.json) · [进度](../../outputs/138_rationale_tasks/progress.md)
