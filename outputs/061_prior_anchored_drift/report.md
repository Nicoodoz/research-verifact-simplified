# 061：Prior-Anchored Class-specific Drift Estimation

## 核心问题

061只改变060的一件事：target prior固定，不再与12维class-specific drift一起自由更新。Oracle-fixed用于诊断上限，BBSE-fixed用于0标签可部署检验。

## GT盲BBSE-fixed实际结果

| source→target | BBSE pi(S/NS/NA) | effective mass(S/NS/NA) |
|---|---|---|
| 052→053 | 0.816/0.064/0.119 | 197.0/12.2/27.8 |
| 053→052 | 0.785/0.068/0.147 | 171.4/22.9/41.7 |

actual_unlabeled.csv先写入并记录SHA256，随后才生成Oracle与GT评价。

## 解盲评价

| source→target | mode | prior L1 | delta MAE | R2 | sign acc | 060 free-prior R2 |
|---|---|---:|---:|---:|---:|---:|
| 052→053 | bbse | 0.023 | 0.662 | 0.300 | 0.417 | 0.004 |
| 052→053 | oracle | 0.000 | 0.653 | 0.307 | 0.583 | 0.004 |
| 053→052 | bbse | 0.031 | 0.755 | 0.066 | 0.500 | -0.254 |
| 053→052 | oracle | 0.000 | 0.750 | 0.097 | 0.417 | -0.254 |

## Synthetic n=960

### oracle
- prior L1 mean: **0.000**
- delta MAE mean: **0.407**
- delta R2 mean: **-2.223**
- nonzero sign accuracy: **96.78%**

### bbse
- prior L1 mean: **0.092**
- delta MAE mean: **0.428**
- delta R2 mean: **-2.523**
- nonzero sign accuracy: **96.04%**

## 结论

**连Oracle固定prior也未通过。**

因此060失败不能只归咎于prior-drift confounding；当前12维Gaussian class-specific drift表示/latent assignment本身仍不足，需要低秩或更强结构约束。

## 边界

- Oracle prior是GT知情诊断，不是部署方法。
- BBSE-fixed才是0标签可部署分支。
- 052/053仍是development内部batch。
- 0 API、未使用reserved、未自动commit/push。
## 失败机制补充

061进一步排除了“只要固定prior就够”的解释。

- 真实052→053：060 free-prior R2=0.004；BBSE-fixed提高到0.300；Oracle-fixed提高到0.307。
- 真实053→052：060为-0.254；BBSE-fixed提高到0.066；Oracle-fixed提高到0.097。

因此固定prior确实缓解了一部分confounding，但远不足以恢复真实class-specific drift。

更关键的是，n=960 synthetic的Oracle-fixed分组显示：真实无漂移的none条件仍产生约0.425的delta MAE；mixed相对最好，R2约0.42；多个单一class×feature漂移的R2仍为负。

这说明当前source-anchored Gaussian mixture会把类内非高斯形状、有限样本波动或component overlap误解释为mean drift。真正瓶颈已经从“prior未知”转向“latent mixture / drift表示不够可识别、也不够稳健”。

同时，BBSE本身在真实两方向仍非常准确（prior L1=0.023/0.031），n=960 synthetic平均prior L1约0.092。因此现阶段没有证据把主要问题归咎于BBSE prevalence sensor。
