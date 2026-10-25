# 023独立审计交接

状态：执行与执行者自检完成，**待独立审计**。正式[主报告](report.md)；最终HEAD、工作区与SHA256清单为`handoff_001.json`。没有宣称独立PASS，没有自动commit/push。

## 重点核查

1. 023是固定λ=2的响应分析，不是搜索winner。协议在生成新曲线前固定401点、精确切换、局部δ及形状摘要标准；任何最高台阶只描述，不改2或开展参数确认。
2. 019七旧点与020两轮U0/U2在绘图前已逐条复现；33组作者分层PA/MCC/AC1/per_class/混淆矩阵完全一致。输入绑定已审022对齐及019/020冻结预测/指标与原scoring映射；未新增原临床文本深读或API。
3. 三个主组分别650/879/879，pooled1529只含R0。020两轮同879条，不能合并为1758独立样本。各组包含all/human/llm及患者曲线。
4. common023使用原math.log/max/floor与NS、NA、S平分顺序；同分后S必须严格胜出。理论t与第一个S的binary64浮点分别保存，前一个可表示浮点为non-S。PDF按精确状态阶梯，不用平滑掩盖跳点。
5. λ=2的平台三组同为[1.9459101490553132,2.079441541679836)，但这是离散生成评分产生的局部平台；不是所有潜在概率/新后端都稳健。±.05不变、±.1可改变多个claim，020 R0/R1上调至2.1分别净+8/−3，正文应如实保留。
6. 预定义“近U2”PA−1pp/MCC−.02的区域与“距曲线最高值”区域不同，summary同时保留；不将区域误称置信区间、非劣性、临床安全或新推荐范围。默认没有bootstrap/p值。
7. R/H/W相对U0：019 λ2为46/8/11，020 R0为83/15/13，R1为89/11/24；Δcorrect=R−H，新增false-S=H+W。患者对B与对U0的净收益分开。
8. 去掉任一患者后三组λ2−U0 PA/MCC仍正，不等于最高台阶固定。019峰位会因患者权重移动，020 R1部分排除后峰移向1.61–1.79；LLM类别极不均衡，MCC曲线不能由PA替代。
9. 022全局λ范围和预测只作已冻结结果解释。固定1.75是事前局部δ=.25产生的诊断点，与022 G/C在2408份评分同标签；不是选择1.75或重新训练022。
10. 图：Figure1/2及S1均PDF/SVG/400dpiPNG；真实PDF用pdftoppm渲染检查，图形清晰不裁字。图和正文没有标“optimal λ”；固定2保持。API_POLICY、原数据、019–022源码/回执/报告及.gitignore不变。

## 安全离线复核

仓库根目录，输出必须不存在；仅允许023目录下新直接子目录或outputs/replays下新目录。禁止网络、不读取key、不加载BGE、不运行旧任务生成器。

```powershell
& 'E:/miniconda3/envs/research-verifact/python.exe' -B tasks/023_lambda_boundary_response_analysis/test023.py
& 'E:/miniconda3/envs/research-verifact/python.exe' -B -m unittest discover -s tests -p test_evaluation.py -q
& 'E:/miniconda3/envs/research-verifact/python.exe' -B tasks/023_lambda_boundary_response_analysis/verify023.py --output outputs/replays/audit023
```

复核校验源manifest、1,578,737个密集标签（含描述性pooled的重复计算，不是独立样本数）、单向计数和二进制切换边界，再重建16个分析文件＋3个患者描述文件。已有[verification_001](verification_001/summary.json)全部一致；原PDF哈希、来源数据及文本结构也通过。

可选图重放用已有research环境Matplotlib3.5.1，数据只取上述新重放输出，不拟合/调参：

```powershell
& 'E:/miniconda3/envs/research/python.exe' -B tasks/023_lambda_boundary_response_analysis/plot023.py --data outputs/replays/audit023/analysis --output outputs/replays/audit023/figures
```

统计环境没有安装matplotlib，因此复用既有research仅作图，environment.yml未改变。跨绘图版本字节可能不同，但必须保留曲线数据、端点/刻度、固定λ线、false-S分母与分组；原图字节以handoff为准。

交付后停止改动同批成果。独立审计通过后再决定最终方法冻结/保留测试事项；本交接不授权024或reserved40。
