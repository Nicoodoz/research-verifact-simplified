# 原052边界解的收敛判据核对（未改配方）

用户确认AutoDL关闭后，首次离线校准在评价GT连接前停于原052求解器的success断言。其实际输出已是theta=-6（预定下界）、损失5.229353472190544、导数+0.06271520942077263。原实现用无约束梯度接近0判断success，所以在合法边界解上返回False。

保持原142条共同有效训练监督、原NLL+0.01theta²、[-6,6]、log-score floor及原052返回的theta=-6不变。仅以约束KKT核验：下界导数非负，投影梯度为0；目标有正Hessian、严格凸，故该解为范围内最优。独立Scipy同目标求解返回-5.9999998668，损失差约8.35e-9。两个端点导数同正，不扩范围，不搜索其他损失，不用评价GT选解。

新增bounded_fit096.py记录constrained_optimum_verified，但保留原success=False、原message及原参数，不能谎称原求解器无约束收敛。历史052和此前calibration096.py不修改。此修复在评价结果产生前完成；详细原始数值见calibration_numerical_diagnostic.json。
