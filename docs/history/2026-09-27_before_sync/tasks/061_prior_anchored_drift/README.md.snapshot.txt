# 061：Prior-Anchored Class-specific Drift Estimation

061只验证一个问题：把target prior固定后，060的12维class-specific drift能否恢复。

Oracle-fixed prior作为诊断上限；BBSE-fixed prior作为0标签部署版本；060 joint-free作为历史基线。

结果：Oracle固定prior能提高真实R2，但仍未过门槛。n=960 Oracle synthetic delta MAE=0.407；真实R2仅0.307/0.097。BBSE实际prior非常准（L1=0.023/0.031），因此060的主要瓶颈不是BBSE，而是当前Gaussian latent mixture / 12维mean-shift表示本身。

0 API、未使用reserved、未自动commit/push。
