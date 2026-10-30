# 123 claim_only_control

状态：9B claim-only 对照已准备，未提取其真实表示、未拟合其读出头、无该对照分类成绩；廉价 TF-IDF 补充控制已完成。

本轮诊断与 118 的 `sqrt_weight_full` 匹配：原 40 名训练患者的 3675 条、原 20 名选型患者的 1817 条，冻结 107 `label_only` 骨干、原 prompt 和公共 4-token verdict 前缀；唯一输入变化为 `reference=""`。保留完整 claim 和原医生 GT，不因拿掉证据将标签改成 NA。继续使用 MLP128、ReLU、dropout 0.1、AdamW lr 0.001、weight decay 0.01、batch64、seed117、平方根类权重 β=0.5、固定 10 轮，训练集单独拟合 StandardScaler，不重新选轮数或超参。

- CPU 准备：`prepare123.py`，私有小包及 GT-free 输入在 `.local_models/123_claim_only_control/`；复用 `extract117.py`，BF16、batch8，OOM 时仅降低 batch，不截断或漏样本。
- GPU 只提取这 5492 条新空 reference 表示；不重新编码或推理全 reference 侧，不训练骨干。隔离目录 `/root/autodl-tmp/verifact123` 使用 122 的现行资源记录原样副本：2026-10-30 12:57:46 至 20:57:46，API80 元累计不重置。旧 117 的 14:55 截止记录不改，也不作为 123 的截止。
- 提取完成后 CPU 入口：`fit123.py --features <回传的 features123_claim_only 目录>`。先验证完整 ID、原107来源和实际空 reference 输入长度，固定拟合一次，然后与已经保存的 118 全 reference 1817 条逐例结果比较。
- `fit123.py --self-test` 只运行小合成 CPU 保存/恢复检查，不代表真实效果。
- 原117 MLP的匹配输入控制另用 `fit_mlp_control123.py --features <同一目录>`：保留原1024训练／730验证的32／8患者、seed117及完整40轮上限／8轮耐心的内部验证选轮流程；不强制沿用全reference侧选中的第6轮。它与全3675固定10轮平方根权重控制并列，复用同一5492条新表示，不增加GPU提取。当前仅执行 `--prepare-only`，尚未拟合。

实际输入共 1,949,281 tokens，单条 345–390，中位数 354；batch8 共 687 批。私有包约 0.66 MB，原文和特征不公开。新短输入吞吐尚待首批正式结果确认，预估加载与提取 10–25 分钟，回传两处隐藏态约 180 MB；CPU 固定头拟合通常在数分钟内。

已另补一次最便宜的同 ID 词面控制：`tfidf_control123.py` 完全沿用 106 的词 unigram/bigram TF-IDF 与无类权重 LR(C=1)，仅在原 40 人 3675 条上拟合一次，评价当前 20 人 1817 条。MCC 0.32755、正确 1502/1817、false-S 298/362；同 ID 的 118 全 reference 平方根权重头为 0.57037、1504/1817、56/362。它表明单看 PA 会严重掩盖非 S 损失，仍不回答同一个 9B 表示去掉 reference 后能保留多少能力；旧 106 OOF 保持不变。参见 [简报](../../outputs/123_claim_only_control/report.md) 和 [完整聚合指标](../../outputs/123_claim_only_control/results_tfidf.json)；模型、词表与系数仍在私有 `tfidf_control/`。

该对照用于判断现有数据与固定配方下 reference 是否带来增量，不是无证据临床核验器，也不能单独证明模型的证据利用因果机制。方法诊断参考 [Poliak et al., Hypothesis Only Baselines in Natural Language Inference (*SEM 2018)](https://aclanthology.org/S18-2023/)，不将通用 NLI 结论或标签定义直接套到 VeriFact。
