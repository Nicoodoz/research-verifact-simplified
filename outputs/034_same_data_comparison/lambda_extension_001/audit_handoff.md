# 034 λ扩展交接

已完成：旧022复现/重复、40人患者外比较、024双向参数迁移与目标模型重拟合、概率分解、类别与患者统计、4组PNG/SVG图及自检。非独立审计。

运行目录：run_001。原034三方对比保持不变，未运行reserved40或调用收费API。未提交/推送。

使用既有research-verifact-029环境，从仓库根运行：

```powershell
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -u -B tasks/034_same_data_comparison/lambda_run_snapshot_001/run.py --output outputs/034_same_data_comparison/lambda_extension_replay_NEW
```

复查入口为同目录verify.py --run <运行目录>。它会重拟合16组低维参数并写入verification.json；为保持正式交付指纹，审计应在运行目录的副本上执行，不直接覆盖正式verification.json。

优先核对：U2温度缩放的标签不变但Brier退化；主40人双约束只剩U2状态；联合NLL在λ=4边界且标签等于U4；辅助多类偏置/Vector的NS损失；患者隔离、概率区间与旧022逐条匹配。

执行期间有并行目录改名，说明及源文件指纹见任务快照snapshot_origin.json、path_amendment.json和运行freeze.json；其他035目录未回写。所有结论以本轮实际结果为准，不以方法名称或自检通过替代有效性证据。
