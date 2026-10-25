# 064 当前状态

064已完成主实验、patient-disjoint future validation、Exposure Fix（Amendment 002）与executor-side verification。verification_001.json共29项PASS。0 API，未使用reserved，未commit/push，独立审计未执行。

## 核心方法

不再估完整target Judge reliability，也不重建分类器。

固定Frozen PriorG为BASE，只定义6个局部policy：
- BASE
- V80 / V60：BASE=S且Qwen强non-S时veto
- R90：BASE=non-S且Qwen Supported>=90时rescue为S
- C80 / C60：对应rescue+veto组合

source只提供每个policy-signature的弱类别先验（等效1个target label）。target few labels只用于认证局部policy；证据不足回退BASE。

## Oracle诊断

完整target GT仅作事后诊断：
- 052→053：oracle-safe policy = **R90**
  - correct +5
  - PA 83.54% → 85.65%
  - MCC 0.5596 → 0.5905
  - rescue false-rescue rate = 1/6 = 16.7%
  - NS/NA recall不下降
- 053→052：oracle = **BASE**
  - R90 correct gain=0
  - false-rescue rate=66.7%
  - NS recall下降

因此同一局部rescue在两个环境的可靠性确实不同，正是064要解决的问题。

## Zero-label

完整target GT-blind阶段两个方向均选择BASE。
结论：当前0标签信息可以安全回退，但不足以认证052→053的R90收益。

## 主same-batch few-label

052→053 active_policy：
- budget5：R90选择46%，unsafe=0
- budget10：18%
- budget20：0%

后两者下降主要因为被标注的R90 action region从同一holdout中被移除，不能用于future泛化解释。

053→052：
- budget5与20可100%回退BASE；
- 但整体两方向没有同一budget通过预注册闭链标准。

## Patient-disjoint Amendment 001

发现实现语义问题：policy exposure错误使用了“calibration剩余未标注action count”。当calibration action region被标完时会把future policy误判为没有作用对象。

该结果已标记superseded，不删除。

## Amendment 002：Future-policy Exposure Fix（最终解释依据）

calibration/future按sid完全分离；few labels来自calibration patients，policy应用于future patients。policy作用规模使用完整calibration无标签signature分布，不再因为标注耗尽而归零。

052→053 active_policy：
- b3：R90 0%
- b5：R90 48%，unsafe 0%，future ΔPA +0.81pp，ΔMCC +0.0094
- b10：R90 **58%**，unsafe 0%，future ΔPA **+1.06pp**，ΔMCC **+0.0127**
- b20：R90 58%，实际平均只需13.9个action-region labels后已无更多分歧样本可标

053→052 active_policy：
- b5：BASE fallback 90%，unsafe 10%
- b10：BASE 88%，unsafe 12%
- b20：BASE 90%，unsafe 10%

因此没有budget满足两方向全部预注册标准：
- forward要求safe beneficial nonBASE selection >=70%，最高仅58%；
- reverse要求BASE fallback>=90%且平均性能不下降，边界上仍有少量误切换/小幅负均值。

## 为什么forward卡在58%

R90 target053只有6条claim，但分散在6个不同患者；patient-half calibration平均只能看到约3条R90实例。

R90真实组成是5 Supported + 1 Not Addressed。少量calibration患者有时足以证明rescue低风险，有时样本包含NA或实例过少，posterior无法越过80% gain证据 + 25%风险阈值。

所以当前主要瓶颈已从“标签总数”进一步缩小到：
**需要积累多少个action-region专属标签，而不是总共标多少条claim。**

## 当前结论

064未达到预注册“missing link closed”标准，但比063明显推进：
1. 找到了真实环境相关、可解释的局部policy；
2. 0标签可以安全回退；
3. 少标签从“重建分类器导致NS崩溃”改善为“0次forward unsafe switch + 正向小幅收益”；
4. 真正剩余问题是稀有action region的证据积累/认证效率。

详见report.md、future_v2_report.md、verification_001.json。
