# 062 当前状态

062已完成正式执行与executor-side核验，verification_001.json共21项PASS；0 API，未使用reserved，未commit/push，独立审计未执行。

目标：用BBSE固定target prior，放弃060/061的Gaussian latent mixture；改为source class empirical distribution + RFF/MMD的低秩transport。主模型rank-1：delta_y=a_y v；rank-2只作诊断。

## Synthetic n=960主结果

- none false-accept = **0.0%**
- 四个rank-1真值pattern平均accept = **58.75%**
- active-coordinate delta MAE = **0.607**
- inactive spurious MAE = **0.110**
- sign accuracy = **55.0%**
- 事前synthetic门槛：**FAIL**

按pattern拆分：
- S_QS_down：accept 82.5%，active MAE 0.135，sign 82.5%；
- NS_QNS：accept 67.5%，active MAE 0.680，sign 65.0%；
- NS_DSNS：accept 45.0%，active MAE 0.685，sign 45.0%；
- NA_DSS：accept 40.0%，active MAE 0.928，sign 27.5%。

结论：source-null校准成功抑制了061式伪漂移，但少数类NS/NA的class-specific drift仍难从无标签混合分布中恢复。

## 真实052↔053

BBSE prior仍准确：
- 052→053 L1=0.02276；
- 053→052 L1=0.03119。

GT解盲后真实3×4 mean-shift矩阵确实高度低秩：
- rank-1 explained energy = **0.90244**
- rank-2 explained energy = **0.99455**

但GT-blind holdout检验：
- 052→053 rank-1 gain=-0.0090 < q95=0.00069，reject；
- 053→052 rank-1 gain=-0.00433 < q95=0.00087，reject；
- 两个rank-2方向也均reject。

因此安全规则下rank-1/rank-2最终delta均回退0，实际R2=0。061 Gaussian fixed-prior R2曾为0.300/0.066，虽有拟合但缺乏可靠holdout支持。

## Rank-2 diagnostic

synthetic mixed：
- accept mean=100%
- delta MAE=0.614
- delta R2=-0.936

因此rank-2也不值得直接正式化。

## 当前结论

“真实mean drift高度低秩”这个诊断成立，但“把source每类经验score分布做低秩整体平移”并不能稳定恢复Judge reliability drift。尤其NS/NA少数类仍是不可识别瓶颈。

不进入dynamic decision。下一步不应继续堆同类transport参数。

详见report.md。
