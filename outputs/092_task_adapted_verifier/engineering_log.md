# 092 工程记录

训练成绩产生前完成以下处理；不把接口或环境失败作为方法阴性。

- 032 GPU venv通过conda research运行，torch2.8.0+cu128、transformers4.56.1、RTX3060 Laptop 6GB可用。
- 本地C48脚本直接导入旧009时，GPU环境缺少旧API链间接要求的duckdb。改为从冻结源AST加载纯检索/packing函数，不安装或改动历史环境。144条原009 reference逐字重放通过。
- 原材料构造中的fingerprint定位改为原pilot接口，准备首次成功后形成9065条cohort；没有用失败过程产生科学预测。
- 虚构前向拆分最大绝对差0.0021198；丢弃的合成标签反向实测encoder权重及表示均改变。该预检不是医学评价或训练结果。
- 虚构512-token显存预检：batch2/4/8峰值约985/1127/1411MiB，故缓存使用8窗批量。正式训练前将window microbatch由初始2改8，effective batch仍8条claim；输入、损失、梯度累积、模型和患者均不变。尚无正式分类成绩，变化纯为执行效率。
- 完整C48补齐1075秒，1817条local-BGE来源；其余7248条逐字缓存复用。全部0 API。
- E盘私有activation缓存避免D盘约71GB剩余空间不足；不修改.gitignore、不提交token IDs/原文/大权重。
