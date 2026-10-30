# Native reason check：准备态

当前接续以127的数据与CPU准备授权为准；此60条GPU诊断尚未运行，本阶段不启动。120只继续已经在运行的原定训练及其标签评价。

仅作原生输出诊断，不新增训练、分类头、投票或后处理，不改120的主标签评价。选原500中的20例（S12/NS4/NA4），只按已有107与220的救回/误伤/保持状态及固定hash选样；未使用未来369结果。样本是有目的的诊断集，不用于估计总体准确率。

未微调原9B、107、真实完成后的120-final369各生成20次，共60个首次回执。三者使用同一原103作者式reason必填prompt、完整author reference、BF16 greedy、thinking off、max_new_tokens768。底座只加载一次；base臂用PEFT禁用全部adapter，两微调臂分别激活自己的adapter，不融合权重。每条verdict与reason必须来自同一次生成；无效保留，不重发、不拿旧reason替换，也不纠正标签。paper_r1旧标签仅作CPU侧历史第四行，不要求旧reason；不能用105不同prompt或103不同thinking的缓存替代本次base臂。仅检查逻辑一致性和实际输入是否支持；未知保留。逻辑一致只是必要条件，不证明解释忠实于模型内部推理，也不证明临床正确。相关限制参见[Turpin等，NeurIPS2023](https://proceedings.neurips.cc/paper_files/paper/2023/hash/ed3fea9033a80fea1376299fa7863f4a-Abstract.html)。

CPU准备：运行 `prepare_native_reason_check.py`；固定清单和小包在私有120/native_reason_check目录。实际369完成后，使用同脚本的 `--bind-final369 <training_done.json>` 绑定真实steps369/consumed2945及checkpoint；未绑定时GPU入口会在加载模型前拒绝运行。上传、启动与当前资源session由主执行者统一安排，当前未执行。

预计60次单样本完整prefill与短理由生成约8–15分钟；每次768上限不是预计都生成768，极端全到上限可能更久，首次正式样本后再更新。阶段限时仍为20分钟，并服从当前20:57:46总截止，不重置费用。只加载一个共同底座、两个小适配器，不重建环境或下载底座。
