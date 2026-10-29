# 111指标附录

GT行、预测列，顺序S/NS/NA；各模型同ID共同有效，缺失无效不补。患者配对bootstrap1000次，原标签与患者角色不改。

## 旧自然400

|模型|Macro-F1|Gwet AC1|false-S率|预测S假发现率|
|---|---:|---:|---:|---:|
|105 label_only|0.5791|0.7607|21.52%|5.65%|
|107 label_only|0.5708|0.7478|15.19%|4.21%|
|110 update_quarter（旧500）|0.5706|0.7209|16.46%|4.66%|
|110 update_half|0.5710|0.7039|13.92%|4.00%|
|paper_r1（历史）|0.5427|0.7723|35.44%|8.64%|

|模型/GT|真实数|预测数|precision|recall|F1|
|---|---:|---:|---:|---:|---:|
|105 label_only/S|321|301|94.35%|88.47%|0.9132|
|105 label_only/NS|26|55|18.18%|38.46%|0.2469|
|105 label_only/NA|53|44|63.64%|52.83%|0.5773|
|107 label_only/S|321|285|95.79%|85.05%|0.9010|
|107 label_only/NS|26|42|14.29%|23.08%|0.1765|
|107 label_only/NA|53|73|54.79%|75.47%|0.6349|
|110 update_quarter（旧500）/S|321|279|95.34%|82.87%|0.8867|
|110 update_quarter（旧500）/NS|26|57|14.04%|30.77%|0.1928|
|110 update_quarter（旧500）/NA|53|64|57.81%|69.81%|0.6325|
|110 update_half/S|321|275|96.00%|82.24%|0.8859|
|110 update_half/NS|26|77|15.58%|46.15%|0.2330|
|110 update_half/NA|53|48|62.50%|56.60%|0.5941|
|paper_r1（历史）/S|321|324|91.36%|92.21%|0.9178|
|paper_r1（历史）/NS|26|45|22.22%|38.46%|0.2817|
|paper_r1（历史）/NA|53|31|58.06%|33.96%|0.4286|

105 label_only：`[[284, 29, 8], [8, 10, 8], [9, 16, 28]]`。

107 label_only：`[[273, 28, 20], [7, 6, 13], [5, 8, 40]]`。

110 update_quarter（旧500）：`[[266, 39, 16], [7, 8, 11], [6, 10, 37]]`。

110 update_half：`[[264, 46, 11], [7, 12, 7], [4, 19, 30]]`。

paper_r1（历史）：`[[296, 17, 8], [11, 10, 5], [17, 18, 18]]`。

|half对照|NS救/伤|NA救/伤|患者正确增/降|患者false-S降/增|ΔMCC 95%CI|
|---|---:|---:|---:|---:|---:|
|105 label_only|3/1|5/3|6/10|3/0|[-0.08008181758574201, 0.03955151772777169]|
|107 label_only|6/0|0/10|2/9|1/1|[-0.08619546796321813, 0.008001715978289433]|

|作者/模型|N|MCC|PA|正确|false-S/non-S|
|---|---:|---:|---:|---:|---:|
|human/105 label_only|226|0.5051|73.89%|167|11/72|
|human/107 label_only|226|0.5416|75.22%|170|6/72|
|human/110 update_quarter（旧500）|226|0.5035|72.12%|163|7/72|
|human/110 update_half|226|0.4980|70.80%|160|6/72|
|human/paper_r1（历史）|226|0.4313|72.57%|164|22/72|
|llm/105 label_only|174|0.0107|89.08%|155|6/7|
|llm/107 label_only|174|0.0354|85.63%|149|6/7|
|llm/110 update_quarter（旧500）|174|0.0314|85.06%|148|6/7|
|llm/110 update_half|174|0.0631|83.91%|146|5/7|
|llm/paper_r1（历史）|174|0.0946|91.95%|160|6/7|

覆盖与无效：`{"label_only105": {"expected": 400, "received": 400, "valid": 400, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 79, "observed_false_S": 17, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.21518987341772153, 0.21518987341772153]}, "label_only107": {"expected": 400, "received": 400, "valid": 400, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 79, "observed_false_S": 12, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.1518987341772152, 0.1518987341772152]}, "update_quarter": {"expected": 400, "received": 400, "valid": 400, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 79, "observed_false_S": 13, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.16455696202531644, 0.16455696202531644]}, "update_half": {"expected": 400, "received": 400, "valid": 400, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 79, "observed_false_S": 11, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.13924050632911392, 0.13924050632911392]}, "paper_r1": {"expected": 400, "received": 400, "valid": 400, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 79, "observed_false_S": 28, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.35443037974683544, 0.35443037974683544]}}`。

## 旧压力100

|模型|Macro-F1|Gwet AC1|false-S率|预测S假发现率|
|---|---:|---:|---:|---:|
|105 label_only|0.4749|0.5081|18.00%|100.00%|
|107 label_only|0.4017|0.4222|16.00%|100.00%|
|110 update_quarter（旧500）|0.4664|0.5301|14.00%|100.00%|
|110 update_half|0.4849|0.5560|13.00%|100.00%|
|paper_r1（历史）|0.3449|0.1920|30.00%|100.00%|

|模型/GT|真实数|预测数|precision|recall|F1|
|---|---:|---:|---:|---:|---:|
|105 label_only/S|0|18|0.00%|—|0.0000|
|105 label_only/NS|50|37|78.38%|58.00%|0.6667|
|105 label_only/NA|50|45|80.00%|72.00%|0.7579|
|107 label_only/S|0|16|0.00%|—|0.0000|
|107 label_only/NS|50|20|85.00%|34.00%|0.4857|
|107 label_only/NA|50|64|64.06%|82.00%|0.7193|
|110 update_quarter（旧500）/S|0|14|0.00%|—|0.0000|
|110 update_quarter（旧500）/NS|50|29|86.21%|50.00%|0.6329|
|110 update_quarter（旧500）/NA|50|57|71.93%|82.00%|0.7664|
|110 update_half/S|0|13|0.00%|—|0.0000|
|110 update_half/NS|50|44|75.00%|66.00%|0.7021|
|110 update_half/NA|50|43|81.40%|70.00%|0.7527|
|paper_r1（历史）/S|0|30|0.00%|—|0.0000|
|paper_r1（历史）/NS|50|42|57.14%|48.00%|0.5217|
|paper_r1（历史）/NA|50|28|71.43%|40.00%|0.5128|

105 label_only：`[[0, 0, 0], [12, 29, 9], [6, 8, 36]]`。

107 label_only：`[[0, 0, 0], [10, 17, 23], [6, 3, 41]]`。

110 update_quarter（旧500）：`[[0, 0, 0], [9, 25, 16], [5, 4, 41]]`。

110 update_half：`[[0, 0, 0], [9, 33, 8], [4, 11, 35]]`。

paper_r1（历史）：`[[0, 0, 0], [18, 24, 8], [12, 18, 20]]`。

|half对照|NS救/伤|NA救/伤|患者正确增/降|患者false-S降/增|ΔMCC 95%CI|
|---|---:|---:|---:|---:|---:|
|105 label_only|6/2|3/4|4/1|5/0|[-0.058476708483707014, 0.11153930166244783]|
|107 label_only|17/1|1/7|8/3|3/0|[-0.023397403579404515, 0.32564271011223217]|

|作者/模型|N|MCC|PA|正确|false-S/non-S|
|---|---:|---:|---:|---:|---:|
|human/105 label_only|89|0.4690|69.66%|62|11/89|
|human/107 label_only|89|0.3451|62.92%|56|9/89|
|human/110 update_quarter（旧500）|89|0.4652|69.66%|62|9/89|
|human/110 update_half|89|0.4555|69.66%|62|9/89|
|human/paper_r1（历史）|89|0.1766|48.31%|43|20/89|
|llm/105 label_only|11|0.1100|27.27%|3|7/11|
|llm/107 label_only|11|0.0000|18.18%|2|7/11|
|llm/110 update_quarter（旧500）|11|0.0173|36.36%|4|5/11|
|llm/110 update_half|11|0.2626|54.55%|6|4/11|
|llm/paper_r1（历史）|11|0.0968|9.09%|1|10/11|

覆盖与无效：`{"label_only105": {"expected": 100, "received": 100, "valid": 100, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 100, "observed_false_S": 18, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.18, 0.18]}, "label_only107": {"expected": 100, "received": 100, "valid": 100, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 100, "observed_false_S": 16, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.16, 0.16]}, "update_quarter": {"expected": 100, "received": 100, "valid": 100, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 100, "observed_false_S": 14, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.14, 0.14]}, "update_half": {"expected": 100, "received": 100, "valid": 100, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 100, "observed_false_S": 13, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.13, 0.13]}, "paper_r1": {"expected": 100, "received": 100, "valid": 100, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 100, "observed_false_S": 30, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.3, 0.3]}}`。

## 新增1317

|模型|Macro-F1|Gwet AC1|false-S率|预测S假发现率|
|---|---:|---:|---:|---:|
|105 label_only|0.6194|0.8131|18.58%|3.30%|
|107 label_only|0.6236|0.7923|12.02%|2.26%|
|110 update_half|0.5991|0.7569|10.93%|2.10%|
|paper_r1（历史）|0.5594|0.8303|25.68%|4.30%|

|模型/GT|真实数|预测数|precision|recall|F1|
|---|---:|---:|---:|---:|---:|
|105 label_only/S|1134|1029|96.70%|87.74%|0.9200|
|105 label_only/NS|45|176|14.20%|55.56%|0.2262|
|105 label_only/NA|138|112|79.46%|64.49%|0.7120|
|107 label_only/S|1134|972|97.74%|83.77%|0.9022|
|107 label_only/NS|45|171|14.62%|55.56%|0.2315|
|107 label_only/NA|138|174|66.09%|83.33%|0.7372|
|110 update_half/S|1134|953|97.90%|82.28%|0.8941|
|110 update_half/NS|45|243|12.35%|66.67%|0.2083|
|110 update_half/NA|138|121|74.38%|65.22%|0.6950|
|paper_r1（历史）/S|1134|1094|95.70%|92.33%|0.9399|
|paper_r1（历史）/NS|45|146|13.01%|42.22%|0.1990|
|paper_r1（历史）/NA|138|77|75.32%|42.03%|0.5395|

105 label_only：`[[995, 121, 18], [15, 25, 5], [19, 30, 89]]`。

107 label_only：`[[950, 134, 50], [11, 25, 9], [11, 12, 115]]`。

110 update_half：`[[933, 175, 26], [10, 30, 5], [10, 38, 90]]`。

paper_r1（历史）：`[[1047, 71, 16], [23, 19, 3], [24, 56, 58]]`。

|half对照|NS救/伤|NA救/伤|患者正确增/降|患者false-S降/增|ΔMCC 95%CI|
|---|---:|---:|---:|---:|---:|
|105 label_only|5/0|8/7|1/17|9/0|[-0.052353122377005124, -0.004906165440943146]|
|107 label_only|5/0|1/26|3/11|2/1|[-0.0903642639262587, -0.010443784444154202]|

下列95%CI均为half减基线，单位为百分点；每次按患者成组配对抽样。

|基线|ΔPA CI|Δfalse-S率 CI|ΔS召回 CI|ΔNS召回 CI|ΔNA召回 CI|
|---|---:|---:|---:|---:|---:|
|105 label_only|[-5.62, -2.93]|[-12.12, -4.08]|[-7.17, -3.94]|[+2.38, +21.05]|[-1.89, +4.92]|
|107 label_only|[-4.92, -0.98]|[-4.11, +0.97]|[-2.61, -0.36]|[+2.94, +19.30]|[-25.93, -9.03]|

|作者/模型|N|MCC|PA|正确|false-S/non-S|
|---|---:|---:|---:|---:|---:|
|human/105 label_only|709|0.5340|77.29%|548|24/165|
|human/107 label_only|709|0.5519|75.88%|538|14/165|
|human/110 update_half|709|0.5150|72.92%|517|12/165|
|human/paper_r1（历史）|709|0.4814|78.14%|554|38/165|
|llm/105 label_only|608|0.2124|92.27%|561|10/18|
|llm/107 label_only|608|0.2573|90.79%|552|8/18|
|llm/110 update_half|608|0.1955|88.16%|536|8/18|
|llm/paper_r1（历史）|608|0.2460|93.75%|570|9/18|

覆盖与无效：`{"label_only105": {"expected": 1317, "received": 1317, "valid": 1317, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 183, "observed_false_S": 34, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.18579234972677597, 0.18579234972677597]}, "label_only107": {"expected": 1317, "received": 1317, "valid": 1317, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 183, "observed_false_S": 22, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.12021857923497267, 0.12021857923497267]}, "update_half": {"expected": 1317, "received": 1317, "valid": 1317, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 183, "observed_false_S": 20, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.1092896174863388, 0.1092896174863388]}, "paper_r1": {"expected": 1317, "received": 1317, "valid": 1317, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 183, "observed_false_S": 47, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.2568306010928962, 0.2568306010928962]}}`。

## 完整1817

|模型|Macro-F1|Gwet AC1|false-S率|预测S假发现率|
|---|---:|---:|---:|---:|
|105 label_only|0.6447|0.7821|19.06%|5.12%|
|107 label_only|0.6260|0.7586|13.81%|3.93%|
|110 update_half|0.6272|0.7289|12.15%|3.55%|
|paper_r1（历史）|0.5780|0.7843|29.01%|7.25%|

|模型/GT|真实数|预测数|precision|recall|F1|
|---|---:|---:|---:|---:|---:|
|105 label_only/S|1455|1348|94.88%|87.90%|0.9126|
|105 label_only/NS|121|268|23.88%|52.89%|0.3290|
|105 label_only/NA|241|201|76.12%|63.49%|0.6923|
|107 label_only/S|1455|1273|96.07%|84.05%|0.8966|
|107 label_only/NS|121|233|20.60%|39.67%|0.2712|
|107 label_only/NA|241|311|63.02%|81.33%|0.7101|
|110 update_half/S|1455|1241|96.45%|82.27%|0.8880|
|110 update_half/NS|121|364|20.60%|61.98%|0.3093|
|110 update_half/NA|241|212|73.11%|64.32%|0.6843|
|paper_r1（历史）/S|1455|1448|92.75%|92.30%|0.9252|
|paper_r1（历史）/NS|121|233|22.75%|43.80%|0.2994|
|paper_r1（历史）/NA|241|136|70.59%|39.83%|0.5093|

105 label_only：`[[1279, 150, 26], [35, 64, 22], [34, 54, 153]]`。

107 label_only：`[[1223, 162, 70], [28, 48, 45], [22, 23, 196]]`。

110 update_half：`[[1197, 221, 37], [26, 75, 20], [18, 68, 155]]`。

paper_r1（历史）：`[[1343, 88, 24], [52, 53, 16], [53, 92, 96]]`。

|half对照|NS救/伤|NA救/伤|患者正确增/降|患者false-S降/增|ΔMCC 95%CI|
|---|---:|---:|---:|---:|---:|
|105 label_only|14/3|16/14|1/17|12/0|[-0.04889177054651143, -0.0024667525778077383]|
|107 label_only|28/1|2/43|4/15|5/2|[-0.05713709223684141, 0.01005106509161148]|

下列95%CI均为half减基线，单位为百分点；每次按患者成组配对抽样。

|基线|ΔPA CI|Δfalse-S率 CI|ΔS召回 CI|ΔNS召回 CI|ΔNA召回 CI|
|---|---:|---:|---:|---:|---:|
|105 label_only|[-5.20, -2.65]|[-10.56, -3.86]|[-7.54, -4.11]|[+2.00, +16.45]|[-1.85, +4.17]|
|107 label_only|[-4.06, -0.73]|[-4.43, +0.30]|[-2.92, -0.76]|[+13.51, +30.46]|[-22.22, -11.28]|

|作者/模型|N|MCC|PA|正确|false-S/non-S|
|---|---:|---:|---:|---:|---:|
|human/105 label_only|1024|0.5568|75.88%|777|46/326|
|human/107 label_only|1024|0.5545|74.61%|764|29/326|
|human/110 update_half|1024|0.5355|72.17%|739|27/326|
|human/paper_r1（历史）|1024|0.4835|74.32%|761|80/326|
|llm/105 label_only|793|0.1927|90.67%|719|23/36|
|llm/107 label_only|793|0.2023|88.65%|703|21/36|
|llm/110 update_half|793|0.2233|86.76%|688|17/36|
|llm/paper_r1（历史）|793|0.1854|92.18%|731|25/36|

覆盖与无效：`{"label_only105": {"expected": 1817, "received": 1817, "valid": 1817, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 362, "observed_false_S": 69, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.19060773480662985, 0.19060773480662985]}, "label_only107": {"expected": 1817, "received": 1817, "valid": 1817, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 362, "observed_false_S": 50, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.13812154696132597, 0.13812154696132597]}, "update_half": {"expected": 1817, "received": 1817, "valid": 1817, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 362, "observed_false_S": 44, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.12154696132596685, 0.12154696132596685]}, "paper_r1": {"expected": 1817, "received": 1817, "valid": 1817, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 362, "observed_false_S": 105, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.2900552486187845, 0.2900552486187845]}}`。

## 103原自然120

|模型|Macro-F1|Gwet AC1|false-S率|预测S假发现率|
|---|---:|---:|---:|---:|
|105 label_only|0.5962|0.7177|20.83%|5.95%|
|107 label_only|0.5361|0.6355|16.67%|5.26%|
|110 update_half|0.5537|0.6223|12.50%|4.05%|
|paper_r1（历史）|0.5289|0.7233|25.00%|6.67%|
|103 nine_lora（512）|0.6509|0.8301|29.17%|7.22%|

|模型/GT|真实数|预测数|precision|recall|F1|
|---|---:|---:|---:|---:|---:|
|105 label_only/S|96|84|94.05%|82.29%|0.8778|
|105 label_only/NS|8|20|20.00%|50.00%|0.2857|
|105 label_only/NA|16|16|62.50%|62.50%|0.6250|
|107 label_only/S|96|76|94.74%|75.00%|0.8372|
|107 label_only/NS|8|21|14.29%|37.50%|0.2069|
|107 label_only/NA|16|23|47.83%|68.75%|0.5641|
|110 update_half/S|96|74|95.95%|73.96%|0.8353|
|110 update_half/NS|8|30|16.67%|62.50%|0.2632|
|110 update_half/NA|16|16|56.25%|56.25%|0.5625|
|paper_r1（历史）/S|96|90|93.33%|87.50%|0.9032|
|paper_r1（历史）/NS|8|22|18.18%|50.00%|0.2667|
|paper_r1（历史）/NA|16|8|62.50%|31.25%|0.4167|
|103 nine_lora（512）/S|96|97|92.78%|93.75%|0.9326|
|103 nine_lora（512）/NS|8|8|37.50%|37.50%|0.3750|
|103 nine_lora（512）/NA|16|15|66.67%|62.50%|0.6452|

105 label_only：`[[79, 13, 4], [2, 4, 2], [3, 3, 10]]`。

107 label_only：`[[72, 15, 9], [2, 3, 3], [2, 3, 11]]`。

110 update_half：`[[71, 19, 6], [2, 5, 1], [1, 6, 9]]`。

paper_r1（历史）：`[[84, 10, 2], [3, 4, 1], [3, 8, 5]]`。

103 nine_lora（512）：`[[90, 4, 2], [2, 3, 3], [5, 1, 10]]`。

|half对照|NS救/伤|NA救/伤|患者正确增/降|患者false-S降/增|ΔMCC 95%CI|
|---|---:|---:|---:|---:|---:|
|103 nine_lora（512）|2/0|0/1|1/11|4/0|[-0.2892902776302374, -0.030933153572588152]|
|105 label_only|1/0|0/1|2/8|2/0|[-0.11763804124365601, 0.019792727772479972]|
|107 label_only|2/0|0/2|2/4|1/0|[-0.08532100445207137, 0.08868226746253331]|

|作者/模型|N|MCC|PA|正确|false-S/non-S|
|---|---:|---:|---:|---:|---:|
|human/105 label_only|68|0.4935|72.06%|49|4/22|
|human/107 label_only|68|0.3922|61.76%|42|3/22|
|human/110 update_half|68|0.4484|64.71%|44|2/22|
|human/paper_r1（历史）|68|0.3804|66.18%|45|5/22|
|human/103 nine_lora（512）|68|0.5739|79.41%|54|5/22|
|llm/105 label_only|52|0.0869|84.62%|44|1/2|
|llm/107 label_only|52|0.0853|84.62%|44|1/2|
|llm/110 update_half|52|0.0528|78.85%|41|1/2|
|llm/paper_r1（历史）|52|0.3278|92.31%|48|1/2|
|llm/103 nine_lora（512）|52|-0.0209|94.23%|49|2/2|

覆盖与无效：`{"label_only105": {"expected": 120, "received": 120, "valid": 120, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 24, "observed_false_S": 5, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.20833333333333334, 0.20833333333333334]}, "label_only107": {"expected": 120, "received": 120, "valid": 120, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 24, "observed_false_S": 4, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.16666666666666666, 0.16666666666666666]}, "update_half": {"expected": 120, "received": 120, "valid": 120, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 24, "observed_false_S": 3, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.125, 0.125]}, "paper_r1": {"expected": 120, "received": 120, "valid": 120, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 24, "observed_false_S": 6, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.25, 0.25]}, "lora103_9b512": {"expected": 120, "received": 120, "valid": 120, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 24, "observed_false_S": 7, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.2916666666666667, 0.2916666666666667]}}`。

## 103原压力60

|模型|Macro-F1|Gwet AC1|false-S率|预测S假发现率|
|---|---:|---:|---:|---:|
|105 label_only|0.4689|0.5107|16.67%|100.00%|
|107 label_only|0.3800|0.4405|11.67%|100.00%|
|110 update_half|0.4821|0.5631|11.67%|100.00%|
|paper_r1（历史）|0.4020|0.3375|23.33%|100.00%|
|103 nine_lora（512）|0.3812|0.2786|35.00%|100.00%|

|模型/GT|真实数|预测数|precision|recall|F1|
|---|---:|---:|---:|---:|---:|
|105 label_only/S|0|10|0.00%|—|0.0000|
|105 label_only/NS|30|20|80.00%|53.33%|0.6400|
|105 label_only/NA|30|30|76.67%|76.67%|0.7667|
|107 label_only/S|0|7|0.00%|—|0.0000|
|107 label_only/NS|30|9|88.89%|26.67%|0.4103|
|107 label_only/NA|30|44|61.36%|90.00%|0.7297|
|110 update_half/S|0|7|0.00%|—|0.0000|
|110 update_half/NS|30|22|81.82%|60.00%|0.6923|
|110 update_half/NA|30|31|74.19%|76.67%|0.7541|
|paper_r1（历史）/S|0|14|0.00%|—|0.0000|
|paper_r1（历史）/NS|30|29|62.07%|60.00%|0.6102|
|paper_r1（历史）/NA|30|17|82.35%|46.67%|0.5957|
|103 nine_lora（512）/S|0|21|0.00%|—|0.0000|
|103 nine_lora（512）/NS|30|9|88.89%|26.67%|0.4103|
|103 nine_lora（512）/NA|30|30|73.33%|73.33%|0.7333|

105 label_only：`[[0, 0, 0], [7, 16, 7], [3, 4, 23]]`。

107 label_only：`[[0, 0, 0], [5, 8, 17], [2, 1, 27]]`。

110 update_half：`[[0, 0, 0], [4, 18, 8], [3, 4, 23]]`。

paper_r1（历史）：`[[0, 0, 0], [9, 18, 3], [5, 11, 14]]`。

103 nine_lora（512）：`[[0, 0, 0], [14, 8, 8], [7, 1, 22]]`。

|half对照|NS救/伤|NA救/伤|患者正确增/降|患者false-S降/增|ΔMCC 95%CI|
|---|---:|---:|---:|---:|---:|
|103 nine_lora（512）|11/1|3/2|7/2|9/0|[-0.08184699306356286, 0.330172744707671]|
|105 label_only|4/2|2/2|5/2|3/0|[-0.1535708994191665, 0.19789017032954226]|
|107 label_only|10/0|0/4|5/2|1/1|[-0.03284347489050629, 0.32403553098224663]|

|作者/模型|N|MCC|PA|正确|false-S/non-S|
|---|---:|---:|---:|---:|---:|
|human/105 label_only|53|0.4773|71.70%|38|4/53|
|human/107 label_only|53|0.3479|64.15%|34|1/53|
|human/110 update_half|53|0.5182|75.47%|40|1/53|
|human/paper_r1（历史）|53|0.2837|56.60%|30|9/53|
|human/103 nine_lora（512）|53|0.3473|56.60%|30|14/53|
|llm/105 label_only|7|0.1291|14.29%|1|6/7|
|llm/107 label_only|7|0.1291|14.29%|1|6/7|
|llm/110 update_half|7|0.1291|14.29%|1|6/7|
|llm/paper_r1（历史）|7|0.2000|28.57%|2|5/7|
|llm/103 nine_lora（512）|7|0.0000|0.00%|0|7/7|

覆盖与无效：`{"label_only105": {"expected": 60, "received": 60, "valid": 60, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 60, "observed_false_S": 10, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.16666666666666666, 0.16666666666666666]}, "label_only107": {"expected": 60, "received": 60, "valid": 60, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 60, "observed_false_S": 7, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.11666666666666667, 0.11666666666666667]}, "update_half": {"expected": 60, "received": 60, "valid": 60, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 60, "observed_false_S": 7, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.11666666666666667, 0.11666666666666667]}, "paper_r1": {"expected": 60, "received": 60, "valid": 60, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 60, "observed_false_S": 14, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.23333333333333334, 0.23333333333333334]}, "lora103_9b512": {"expected": 60, "received": 60, "valid": 60, "invalid": 0, "missing": 0, "invalid_GT": {}, "missing_GT": {}, "true_nonS_total": 60, "observed_false_S": 21, "nonS_unknown": 0, "false_S_full_cohort_bounds": [0.35, 0.35]}}`。
