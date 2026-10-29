# 110指标附录

行GT、列预测，S/NS/NA固定三分类。主比较与所有无效覆盖见comparison.json；训练192的诊断不作为方法效果。

## 自然

|配置|Macro-F1|Gwet AC1|false-S率|预测S假发现率|
|---|---:|---:|---:|---:|
|107 label_only|0.5708|0.7478|15.19%|4.21%|
|109 boundary_replay|0.3969|0.6501|13.92%|3.94%|
|update_quarter (.25)|0.5706|0.7209|16.46%|4.66%|
|update_half (.5)|0.5710|0.7039|13.92%|4.00%|
|paper_r1（历史）|0.5427|0.7723|35.44%|8.64%|

|配置/类|真实数|预测数|precision|recall|F1|
|---|---:|---:|---:|---:|---:|
|107 label_only/S|321|285|95.79%|85.05%|0.9010|
|107 label_only/NS|26|42|14.29%|23.08%|0.1765|
|107 label_only/NA|53|73|54.79%|75.47%|0.6349|
|109 boundary_replay/S|321|279|96.06%|83.49%|0.8933|
|109 boundary_replay/NS|26|120|15.83%|73.08%|0.2603|
|109 boundary_replay/NA|53|1|100.00%|1.89%|0.0370|
|update_quarter (.25)/S|321|279|95.34%|82.87%|0.8867|
|update_quarter (.25)/NS|26|57|14.04%|30.77%|0.1928|
|update_quarter (.25)/NA|53|64|57.81%|69.81%|0.6325|
|update_half (.5)/S|321|275|96.00%|82.24%|0.8859|
|update_half (.5)/NS|26|77|15.58%|46.15%|0.2330|
|update_half (.5)/NA|53|48|62.50%|56.60%|0.5941|
|paper_r1（历史）/S|321|324|91.36%|92.21%|0.9178|
|paper_r1（历史）/NS|26|45|22.22%|38.46%|0.2817|
|paper_r1（历史）/NA|53|31|58.06%|33.96%|0.4286|

107 label_only混淆矩阵：`[[273, 28, 20], [7, 6, 13], [5, 8, 40]]`。


109 boundary_replay混淆矩阵：`[[268, 53, 0], [7, 19, 0], [4, 48, 1]]`。


update_quarter (.25)混淆矩阵：`[[266, 39, 16], [7, 8, 11], [6, 10, 37]]`。


update_half (.5)混淆矩阵：`[[264, 46, 11], [7, 12, 7], [4, 19, 30]]`。


paper_r1（历史）混淆矩阵：`[[296, 17, 8], [11, 10, 5], [17, 18, 18]]`。


|候选|ΔMCC 95%CI|ΔPA 95%CI（百分点）|
|---|---:|---:|
|update_quarter|[-0.0606, 0.0062]|[-4.25, 0.0]|
|update_half|[-0.0862, 0.008]|[-5.92, -0.98]|

|作者/配置|N|MCC|PA|false-S|
|---|---:|---:|---:|---:|
|human/107 label_only|226|0.5416|75.22%|6|
|human/109 boundary_replay|226|0.4022|61.95%|6|
|human/update_quarter (.25)|226|0.5035|72.12%|7|
|human/update_half (.5)|226|0.4980|70.80%|6|
|llm/107 label_only|174|0.0354|85.63%|6|
|llm/109 boundary_replay|174|0.0300|85.06%|5|
|llm/update_quarter (.25)|174|0.0314|85.06%|6|
|llm/update_half (.5)|174|0.0631|83.91%|5|

覆盖：`{"label_only107": {"received": 400, "valid": 400, "invalid": 0, "strict_JSON": 400, "exact_label_normalized": 0, "truncated_finish": 0, "invalid_GT": {}}, "boundary_replay109": {"received": 400, "valid": 400, "invalid": 0, "strict_JSON": 400, "exact_label_normalized": 0, "truncated_finish": 0, "invalid_GT": {}}, "update_quarter": {"received": 400, "valid": 400, "invalid": 0, "strict_JSON": 400, "exact_label_normalized": 0, "truncated_finish": 0, "invalid_GT": {}}, "update_half": {"received": 400, "valid": 400, "invalid": 0, "strict_JSON": 400, "exact_label_normalized": 0, "truncated_finish": 0, "invalid_GT": {}}}`。

## 压力

|配置|Macro-F1|Gwet AC1|false-S率|预测S假发现率|
|---|---:|---:|---:|---:|
|107 label_only|0.4017|0.4222|16.00%|100.00%|
|109 boundary_replay|0.1891|0.1830|16.00%|100.00%|
|update_quarter (.25)|0.4664|0.5301|14.00%|100.00%|
|update_half (.5)|0.4849|0.5560|13.00%|100.00%|
|paper_r1（历史）|0.3449|0.1920|30.00%|100.00%|

|配置/类|真实数|预测数|precision|recall|F1|
|---|---:|---:|---:|---:|---:|
|107 label_only/S|0|16|0.00%|—|0.0000|
|107 label_only/NS|50|20|85.00%|34.00%|0.4857|
|107 label_only/NA|50|64|64.06%|82.00%|0.7193|
|109 boundary_replay/S|0|16|0.00%|—|0.0000|
|109 boundary_replay/NS|50|84|45.24%|76.00%|0.5672|
|109 boundary_replay/NA|50|0|—|0.00%|0.0000|
|update_quarter (.25)/S|0|14|0.00%|—|0.0000|
|update_quarter (.25)/NS|50|29|86.21%|50.00%|0.6329|
|update_quarter (.25)/NA|50|57|71.93%|82.00%|0.7664|
|update_half (.5)/S|0|13|0.00%|—|0.0000|
|update_half (.5)/NS|50|44|75.00%|66.00%|0.7021|
|update_half (.5)/NA|50|43|81.40%|70.00%|0.7527|
|paper_r1（历史）/S|0|30|0.00%|—|0.0000|
|paper_r1（历史）/NS|50|42|57.14%|48.00%|0.5217|
|paper_r1（历史）/NA|50|28|71.43%|40.00%|0.5128|

107 label_only混淆矩阵：`[[0, 0, 0], [10, 17, 23], [6, 3, 41]]`。


109 boundary_replay混淆矩阵：`[[0, 0, 0], [12, 38, 0], [4, 46, 0]]`。


update_quarter (.25)混淆矩阵：`[[0, 0, 0], [9, 25, 16], [5, 4, 41]]`。


update_half (.5)混淆矩阵：`[[0, 0, 0], [9, 33, 8], [4, 11, 35]]`。


paper_r1（历史）混淆矩阵：`[[0, 0, 0], [18, 24, 8], [12, 18, 20]]`。


|候选|ΔMCC 95%CI|ΔPA 95%CI（百分点）|
|---|---:|---:|
|update_quarter|[0.0479, 0.2232]|[3.66, 14.29]|
|update_half|[-0.0234, 0.3256]|[0.88, 21.43]|

|作者/配置|N|MCC|PA|false-S|
|---|---:|---:|---:|---:|
|human/107 label_only|89|0.3451|62.92%|9|
|human/109 boundary_replay|89|-0.0960|38.20%|11|
|human/update_quarter (.25)|89|0.4652|69.66%|9|
|human/update_half (.5)|89|0.4555|69.66%|9|
|llm/107 label_only|11|0.0000|18.18%|7|
|llm/109 boundary_replay|11|-0.0745|36.36%|5|
|llm/update_quarter (.25)|11|0.0173|36.36%|5|
|llm/update_half (.5)|11|0.2626|54.55%|4|

覆盖：`{"label_only107": {"received": 100, "valid": 100, "invalid": 0, "strict_JSON": 100, "exact_label_normalized": 0, "truncated_finish": 0, "invalid_GT": {}}, "boundary_replay109": {"received": 100, "valid": 100, "invalid": 0, "strict_JSON": 100, "exact_label_normalized": 0, "truncated_finish": 0, "invalid_GT": {}}, "update_quarter": {"received": 100, "valid": 100, "invalid": 0, "strict_JSON": 100, "exact_label_normalized": 0, "truncated_finish": 0, "invalid_GT": {}}, "update_half": {"received": 100, "valid": 100, "invalid": 0, "strict_JSON": 100, "exact_label_normalized": 0, "truncated_finish": 0, "invalid_GT": {}}}`。
