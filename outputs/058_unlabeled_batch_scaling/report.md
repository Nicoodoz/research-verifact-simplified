# 058：Unlabeled Batch-size Scaling

## 核心结论

058完全复用057 soft detector，只扩大target无标签batch size，检验057失败主要是样本量还是结构性不可识别。

结果表明：**样本量是当前detector的主要瓶颈之一。**

| source | n=240 | n=480 | n=960 | n=1920 |
|---|---:|---:|---:|---:|
| 052 mean H1 detection | 66.3% | 86.9% | **99.4%** | 100% |
| 053 mean H1 detection | 58.5% | 79.9% | **97.4%** | 100% |

H0 false-alarm在各n基本保持约4–6%。

n=960时，两方向平均检测率都超过90%；052六种场景最低97.0%，053最低86.6%。n=1920时，当前六种prior场景、两方向的模拟conditional replacement均达到100% detection。

最难场景主要是NA-heavy：在n=480时052/053方向检测率只有53.8%/42.4%，到n=960升到97.0%/86.6%，n=1920均达到100%。

## 解释

这说明056/057在约240条target claim上失败，不能简单解释为“无标签信息不存在”。在当前经验P(scores|Y)下，随着独立无标签观察增加，soft residual能越来越稳定地区分纯label shift与conditional behavior replacement。

但058不能证明真实部署收集960或1920条claim就一定达到这些检测率。现有052/053只有236/237条，n>该规模是从经验类条件池有放回重采样，表示统计趋势，而不是新真实患者/claim。

## 当前判断

zero-label reliability monitoring仍值得继续研究。下一步不应马上调detector，而应先验证：
1. 更大真实独立claim batch是否复现该scaling；
2. batch应按claim还是按患者有效样本量计算；
3. 真实环境中检测到漂移后，能否进一步指导安全adaptation。

0 API，未使用reserved，未修改057，未自动commit/push。
