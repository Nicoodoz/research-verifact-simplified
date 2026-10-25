# 071 提示与教学来源核对

- 原 VeriFact 固定提交 [`f115d36` 的 `llm_judge/prompts.py`](https://github.com/philipchung/verifact/blob/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/packages/llm_judge/src/llm_judge/prompts.py)有三条**合成** few-shot 示例，分别展示 NS、S、NA；这些不是本数据集医生标注案例。源码中非推理 Judge 调用该 few-shot 模板，而推理 Judge 调用无示例的 reasoning 模板（[judge.py](https://github.com/philipchung/verifact/blob/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/packages/llm_judge/src/llm_judge/judge.py)）。
- 当前 053 冻结 T-S 是另一套 DeepSeek 0731 提示：要求五项 checks、三类 `label_scores`、thinking-high 和严格 JSON schema；系统消息原本无示例。071 只在这套系统消息后增加四条真实、三医生一致示例。B 臂完整请求体与 053 原请求一致；E/C 除追加示例中的医生标签对应或打乱外，目标 claim/reference、模型、schema 与生成参数均固定。
- 四示例的来源、首轮一致性、完整 reference 指纹、节选规则见 [`examples.jsonl`](examples.jsonl)。S 的选段直接陈述完整命题；NS、NA 保留整份 053 final reference。**NA 标签来自医生对原 EHR 的判定**，不能将其当作任何任意裁剪短片段的独立标注。没有由模型撰写“标准 reason”。
- 评价为另 16 名患者的全部 96 条冻结 053 claim，患者与示例无交叉；双方来源 note ID 无交集，最大规范化 claim 相似度 0.7013。[冻结台账](freeze.json)保存具体名单与哈希。对照 C 保留示例文本、格式和标签直方图，仅打乱对应关系。
