# B：统一口径完整诊断表

所有结果为冻结分数的事后诊断，不选择新方法。Original为同ID不同历史系统参照。

## natural：全体176，四臂core共同有效167

|配置（共同有效）|MCC|PA|正确数|错误支持/non-S|Macro-F1|S/NS/NA召回|
|---|---:|---:|---:|---:|---:|---|
|Original|0.4316|79.04%|132/167|10/36|0.5216|91.60%/23.08%/39.13%|
|B/raw|0.3637|68.86%|115/167|7/36|0.5073|74.05%/7.69%/73.91%|
|B/U0|0.3637|68.86%|115/167|7/36|0.5073|74.05%/7.69%/73.91%|
|B/U2|0.4577|77.84%|130/167|8/36|0.5369|85.50%/7.69%/73.91%|
|B/prior_only|0.5270|82.63%|138/167|9/36|0.5559|91.60%/7.69%/73.91%|
|B/PriorG|0.5270|82.63%|138/167|9/36|0.5559|91.60%/7.69%/73.91%|
|F4/raw|0.3705|71.86%|120/167|6/36|0.4703|80.92%/0.00%/60.87%|
|F4/U0|0.3705|71.86%|120/167|6/36|0.4703|80.92%/0.00%/60.87%|
|F4/U2|0.4459|78.44%|131/167|7/36|0.4854|89.31%/0.00%/60.87%|
|F4/prior_only|0.4838|80.84%|135/167|7/36|0.4909|92.37%/0.00%/60.87%|
|F4/PriorG|0.4838|80.84%|135/167|7/36|0.4909|92.37%/0.00%/60.87%|
|P90/raw|0.4619|76.05%|127/167|5/36|0.5450|82.44%/15.38%/73.91%|
|P90/U0|0.4619|76.05%|127/167|5/36|0.5450|82.44%/15.38%/73.91%|
|P90/U2|0.4960|80.84%|135/167|8/36|0.5379|90.08%/7.69%/69.57%|
|P90/prior_only|0.5271|82.63%|138/167|9/36|0.5533|91.60%/7.69%/73.91%|
|P90/PriorG|0.5049|82.04%|137/167|10/36|0.5434|91.60%/7.69%/69.57%|
|Q90/raw|0.4074|72.46%|121/167|5/36|0.5099|79.39%/7.69%/69.57%|
|Q90/U0|0.4074|72.46%|121/167|5/36|0.5099|79.39%/7.69%/69.57%|
|Q90/U2|0.4615|79.04%|132/167|8/36|0.5084|88.55%/0.00%/69.57%|
|Q90/prior_only|0.4938|82.04%|137/167|11/36|0.5118|92.37%/0.00%/69.57%|
|Q90/PriorG|0.4938|82.04%|137/167|11/36|0.5118|92.37%/0.00%/69.57%|

### P−F按GT的正确数增量

|GT|raw净值|最终净值|
|---|---:|---:|
|Supported|+2|-1|
|Not Supported|+2|+1|
|Not Addressed|+3|+2|

### raw到最终的联合正确性路径

|类型|人数（命题）|GT组成|
|---|---:|---|
|final_only_harm|2|{'Not Addressed': 1, 'Supported': 1}|
|no_net_change|154|{'Not Addressed': 19, 'Not Supported': 11, 'Supported': 124}|
|raw_gain_both_final_correct|4|{'Supported': 4}|
|raw_gain_both_final_wrong|1|{'Not Supported': 1}|
|raw_gain_retained|4|{'Not Addressed': 3, 'Not Supported': 1}|
|raw_harm_erased|2|{'Supported': 2}|

### 每类标签转移（含未改标签，完整分区）

|臂|前→后|GT|前标签|后标签|数量|
|---|---|---|---|---|---:|
|B|raw→U0|Not Addressed|Not Addressed|Not Addressed|17|
|B|raw→U0|Not Addressed|Not Supported|Not Supported|4|
|B|raw→U0|Not Addressed|Supported|Supported|2|
|B|raw→U0|Not Supported|Not Addressed|Not Addressed|7|
|B|raw→U0|Not Supported|Not Supported|Not Supported|1|
|B|raw→U0|Not Supported|Supported|Supported|5|
|B|raw→U0|Supported|Not Addressed|Not Addressed|5|
|B|raw→U0|Supported|Not Supported|Not Supported|29|
|B|raw→U0|Supported|Supported|Supported|97|
|B|U0→U2|Not Addressed|Not Addressed|Not Addressed|17|
|B|U0→U2|Not Addressed|Not Supported|Not Supported|3|
|B|U0→U2|Not Addressed|Not Supported|Supported|1|
|B|U0→U2|Not Addressed|Supported|Supported|2|
|B|U0→U2|Not Supported|Not Addressed|Not Addressed|7|
|B|U0→U2|Not Supported|Not Supported|Not Supported|1|
|B|U0→U2|Not Supported|Supported|Supported|5|
|B|U0→U2|Supported|Not Addressed|Not Addressed|5|
|B|U0→U2|Supported|Not Supported|Not Supported|14|
|B|U0→U2|Supported|Not Supported|Supported|15|
|B|U0→U2|Supported|Supported|Supported|97|
|B|U0→prior_only|Not Addressed|Not Addressed|Not Addressed|17|
|B|U0→prior_only|Not Addressed|Not Supported|Not Supported|2|
|B|U0→prior_only|Not Addressed|Not Supported|Supported|2|
|B|U0→prior_only|Not Addressed|Supported|Supported|2|
|B|U0→prior_only|Not Supported|Not Addressed|Not Addressed|7|
|B|U0→prior_only|Not Supported|Not Supported|Not Supported|1|
|B|U0→prior_only|Not Supported|Supported|Supported|5|
|B|U0→prior_only|Supported|Not Addressed|Not Addressed|5|
|B|U0→prior_only|Supported|Not Supported|Not Supported|6|
|B|U0→prior_only|Supported|Not Supported|Supported|23|
|B|U0→prior_only|Supported|Supported|Supported|97|
|B|prior_only→PriorG|Not Addressed|Not Addressed|Not Addressed|17|
|B|prior_only→PriorG|Not Addressed|Not Supported|Not Supported|2|
|B|prior_only→PriorG|Not Addressed|Supported|Supported|4|
|B|prior_only→PriorG|Not Supported|Not Addressed|Not Addressed|7|
|B|prior_only→PriorG|Not Supported|Not Supported|Not Supported|1|
|B|prior_only→PriorG|Not Supported|Supported|Supported|5|
|B|prior_only→PriorG|Supported|Not Addressed|Not Addressed|5|
|B|prior_only→PriorG|Supported|Not Supported|Not Supported|6|
|B|prior_only→PriorG|Supported|Supported|Supported|120|
|B|raw→PriorG|Not Addressed|Not Addressed|Not Addressed|17|
|B|raw→PriorG|Not Addressed|Not Supported|Not Supported|2|
|B|raw→PriorG|Not Addressed|Not Supported|Supported|2|
|B|raw→PriorG|Not Addressed|Supported|Supported|2|
|B|raw→PriorG|Not Supported|Not Addressed|Not Addressed|7|
|B|raw→PriorG|Not Supported|Not Supported|Not Supported|1|
|B|raw→PriorG|Not Supported|Supported|Supported|5|
|B|raw→PriorG|Supported|Not Addressed|Not Addressed|5|
|B|raw→PriorG|Supported|Not Supported|Not Supported|6|
|B|raw→PriorG|Supported|Not Supported|Supported|23|
|B|raw→PriorG|Supported|Supported|Supported|97|
|F4|raw→U0|Not Addressed|Not Addressed|Not Addressed|14|
|F4|raw→U0|Not Addressed|Not Supported|Not Supported|8|
|F4|raw→U0|Not Addressed|Supported|Supported|1|
|F4|raw→U0|Not Supported|Not Addressed|Not Addressed|8|
|F4|raw→U0|Not Supported|Supported|Supported|5|
|F4|raw→U0|Supported|Not Addressed|Not Addressed|7|
|F4|raw→U0|Supported|Not Supported|Not Supported|18|
|F4|raw→U0|Supported|Supported|Supported|106|
|F4|U0→U2|Not Addressed|Not Addressed|Not Addressed|14|
|F4|U0→U2|Not Addressed|Not Supported|Not Supported|7|
|F4|U0→U2|Not Addressed|Not Supported|Supported|1|
|F4|U0→U2|Not Addressed|Supported|Supported|1|
|F4|U0→U2|Not Supported|Not Addressed|Not Addressed|8|
|F4|U0→U2|Not Supported|Supported|Supported|5|
|F4|U0→U2|Supported|Not Addressed|Not Addressed|7|
|F4|U0→U2|Supported|Not Supported|Not Supported|7|
|F4|U0→U2|Supported|Not Supported|Supported|11|
|F4|U0→U2|Supported|Supported|Supported|106|
|F4|U0→prior_only|Not Addressed|Not Addressed|Not Addressed|14|
|F4|U0→prior_only|Not Addressed|Not Supported|Not Supported|7|
|F4|U0→prior_only|Not Addressed|Not Supported|Supported|1|
|F4|U0→prior_only|Not Addressed|Supported|Supported|1|
|F4|U0→prior_only|Not Supported|Not Addressed|Not Addressed|8|
|F4|U0→prior_only|Not Supported|Supported|Supported|5|
|F4|U0→prior_only|Supported|Not Addressed|Not Addressed|7|
|F4|U0→prior_only|Supported|Not Supported|Not Supported|3|
|F4|U0→prior_only|Supported|Not Supported|Supported|15|
|F4|U0→prior_only|Supported|Supported|Supported|106|
|F4|prior_only→PriorG|Not Addressed|Not Addressed|Not Addressed|14|
|F4|prior_only→PriorG|Not Addressed|Not Supported|Not Supported|7|
|F4|prior_only→PriorG|Not Addressed|Supported|Supported|2|
|F4|prior_only→PriorG|Not Supported|Not Addressed|Not Addressed|8|
|F4|prior_only→PriorG|Not Supported|Supported|Supported|5|
|F4|prior_only→PriorG|Supported|Not Addressed|Not Addressed|7|
|F4|prior_only→PriorG|Supported|Not Supported|Not Supported|3|
|F4|prior_only→PriorG|Supported|Supported|Supported|121|
|F4|raw→PriorG|Not Addressed|Not Addressed|Not Addressed|14|
|F4|raw→PriorG|Not Addressed|Not Supported|Not Supported|7|
|F4|raw→PriorG|Not Addressed|Not Supported|Supported|1|
|F4|raw→PriorG|Not Addressed|Supported|Supported|1|
|F4|raw→PriorG|Not Supported|Not Addressed|Not Addressed|8|
|F4|raw→PriorG|Not Supported|Supported|Supported|5|
|F4|raw→PriorG|Supported|Not Addressed|Not Addressed|7|
|F4|raw→PriorG|Supported|Not Supported|Not Supported|3|
|F4|raw→PriorG|Supported|Not Supported|Supported|15|
|F4|raw→PriorG|Supported|Supported|Supported|106|
|P90|raw→U0|Not Addressed|Not Addressed|Not Addressed|17|
|P90|raw→U0|Not Addressed|Not Supported|Not Supported|5|
|P90|raw→U0|Not Addressed|Supported|Supported|1|
|P90|raw→U0|Not Supported|Not Addressed|Not Addressed|7|
|P90|raw→U0|Not Supported|Not Supported|Not Supported|2|
|P90|raw→U0|Not Supported|Supported|Supported|4|
|P90|raw→U0|Supported|Not Addressed|Not Addressed|6|
|P90|raw→U0|Supported|Not Supported|Not Supported|17|
|P90|raw→U0|Supported|Supported|Supported|108|
|P90|U0→U2|Not Addressed|Not Addressed|Not Addressed|16|
|P90|U0→U2|Not Addressed|Not Addressed|Supported|1|
|P90|U0→U2|Not Addressed|Not Supported|Not Supported|4|
|P90|U0→U2|Not Addressed|Not Supported|Supported|1|
|P90|U0→U2|Not Addressed|Supported|Supported|1|
|P90|U0→U2|Not Supported|Not Addressed|Not Addressed|7|
|P90|U0→U2|Not Supported|Not Supported|Not Supported|1|
|P90|U0→U2|Not Supported|Not Supported|Supported|1|
|P90|U0→U2|Not Supported|Supported|Supported|4|
|P90|U0→U2|Supported|Not Addressed|Not Addressed|6|
|P90|U0→U2|Supported|Not Supported|Not Supported|7|
|P90|U0→U2|Supported|Not Supported|Supported|10|
|P90|U0→U2|Supported|Supported|Supported|108|
|P90|U0→prior_only|Not Addressed|Not Addressed|Not Addressed|17|
|P90|U0→prior_only|Not Addressed|Not Supported|Not Supported|2|
|P90|U0→prior_only|Not Addressed|Not Supported|Supported|3|
|P90|U0→prior_only|Not Addressed|Supported|Supported|1|
|P90|U0→prior_only|Not Supported|Not Addressed|Not Addressed|7|
|P90|U0→prior_only|Not Supported|Not Supported|Not Supported|1|
|P90|U0→prior_only|Not Supported|Not Supported|Supported|1|
|P90|U0→prior_only|Not Supported|Supported|Supported|4|
|P90|U0→prior_only|Supported|Not Addressed|Not Addressed|6|
|P90|U0→prior_only|Supported|Not Supported|Not Supported|5|
|P90|U0→prior_only|Supported|Not Supported|Supported|12|
|P90|U0→prior_only|Supported|Supported|Supported|108|
|P90|prior_only→PriorG|Not Addressed|Not Addressed|Not Addressed|16|
|P90|prior_only→PriorG|Not Addressed|Not Addressed|Supported|1|
|P90|prior_only→PriorG|Not Addressed|Not Supported|Not Supported|2|
|P90|prior_only→PriorG|Not Addressed|Supported|Supported|4|
|P90|prior_only→PriorG|Not Supported|Not Addressed|Not Addressed|7|
|P90|prior_only→PriorG|Not Supported|Not Supported|Not Supported|1|
|P90|prior_only→PriorG|Not Supported|Supported|Supported|5|
|P90|prior_only→PriorG|Supported|Not Addressed|Not Addressed|6|
|P90|prior_only→PriorG|Supported|Not Supported|Not Supported|5|
|P90|prior_only→PriorG|Supported|Supported|Supported|120|
|P90|raw→PriorG|Not Addressed|Not Addressed|Not Addressed|16|
|P90|raw→PriorG|Not Addressed|Not Addressed|Supported|1|
|P90|raw→PriorG|Not Addressed|Not Supported|Not Supported|2|
|P90|raw→PriorG|Not Addressed|Not Supported|Supported|3|
|P90|raw→PriorG|Not Addressed|Supported|Supported|1|
|P90|raw→PriorG|Not Supported|Not Addressed|Not Addressed|7|
|P90|raw→PriorG|Not Supported|Not Supported|Not Supported|1|
|P90|raw→PriorG|Not Supported|Not Supported|Supported|1|
|P90|raw→PriorG|Not Supported|Supported|Supported|4|
|P90|raw→PriorG|Supported|Not Addressed|Not Addressed|6|
|P90|raw→PriorG|Supported|Not Supported|Not Supported|5|
|P90|raw→PriorG|Supported|Not Supported|Supported|12|
|P90|raw→PriorG|Supported|Supported|Supported|108|
|Q90|raw→U0|Not Addressed|Not Addressed|Not Addressed|16|
|Q90|raw→U0|Not Addressed|Not Supported|Not Supported|6|
|Q90|raw→U0|Not Addressed|Supported|Supported|1|
|Q90|raw→U0|Not Supported|Not Addressed|Not Addressed|8|
|Q90|raw→U0|Not Supported|Not Supported|Not Supported|1|
|Q90|raw→U0|Not Supported|Supported|Supported|4|
|Q90|raw→U0|Supported|Not Addressed|Not Addressed|5|
|Q90|raw→U0|Supported|Not Supported|Not Supported|22|
|Q90|raw→U0|Supported|Supported|Supported|104|
|Q90|U0→U2|Not Addressed|Not Addressed|Not Addressed|16|
|Q90|U0→U2|Not Addressed|Not Supported|Not Supported|4|
|Q90|U0→U2|Not Addressed|Not Supported|Supported|2|
|Q90|U0→U2|Not Addressed|Supported|Supported|1|
|Q90|U0→U2|Not Supported|Not Addressed|Not Addressed|8|
|Q90|U0→U2|Not Supported|Not Supported|Supported|1|
|Q90|U0→U2|Not Supported|Supported|Supported|4|
|Q90|U0→U2|Supported|Not Addressed|Not Addressed|5|
|Q90|U0→U2|Supported|Not Supported|Not Supported|10|
|Q90|U0→U2|Supported|Not Supported|Supported|12|
|Q90|U0→U2|Supported|Supported|Supported|104|
|Q90|U0→prior_only|Not Addressed|Not Addressed|Not Addressed|16|
|Q90|U0→prior_only|Not Addressed|Not Supported|Not Supported|1|
|Q90|U0→prior_only|Not Addressed|Not Supported|Supported|5|
|Q90|U0→prior_only|Not Addressed|Supported|Supported|1|
|Q90|U0→prior_only|Not Supported|Not Addressed|Not Addressed|8|
|Q90|U0→prior_only|Not Supported|Not Supported|Supported|1|
|Q90|U0→prior_only|Not Supported|Supported|Supported|4|
|Q90|U0→prior_only|Supported|Not Addressed|Not Addressed|5|
|Q90|U0→prior_only|Supported|Not Supported|Not Supported|5|
|Q90|U0→prior_only|Supported|Not Supported|Supported|17|
|Q90|U0→prior_only|Supported|Supported|Supported|104|
|Q90|prior_only→PriorG|Not Addressed|Not Addressed|Not Addressed|16|
|Q90|prior_only→PriorG|Not Addressed|Not Supported|Not Supported|1|
|Q90|prior_only→PriorG|Not Addressed|Supported|Supported|6|
|Q90|prior_only→PriorG|Not Supported|Not Addressed|Not Addressed|8|
|Q90|prior_only→PriorG|Not Supported|Supported|Supported|5|
|Q90|prior_only→PriorG|Supported|Not Addressed|Not Addressed|5|
|Q90|prior_only→PriorG|Supported|Not Supported|Not Supported|5|
|Q90|prior_only→PriorG|Supported|Supported|Supported|121|
|Q90|raw→PriorG|Not Addressed|Not Addressed|Not Addressed|16|
|Q90|raw→PriorG|Not Addressed|Not Supported|Not Supported|1|
|Q90|raw→PriorG|Not Addressed|Not Supported|Supported|5|
|Q90|raw→PriorG|Not Addressed|Supported|Supported|1|
|Q90|raw→PriorG|Not Supported|Not Addressed|Not Addressed|8|
|Q90|raw→PriorG|Not Supported|Not Supported|Supported|1|
|Q90|raw→PriorG|Not Supported|Supported|Supported|4|
|Q90|raw→PriorG|Supported|Not Addressed|Not Addressed|5|
|Q90|raw→PriorG|Supported|Not Supported|Not Supported|5|
|Q90|raw→PriorG|Supported|Not Supported|Supported|17|
|Q90|raw→PriorG|Supported|Supported|Supported|104|

### 患者分布

|患者|共同有效数|raw救回/伤害/净|最终救回/伤害/净|
|---|---:|---|---|
|15057|8|0/0/+0|0/0/+0|
|21706|7|0/0/+0|0/0/+0|
|26858|8|0/0/+0|0/0/+0|
|27036|8|0/1/-1|0/0/+0|
|27823|8|2/1/+1|0/0/+0|
|28399|8|1/0/+1|0/0/+0|
|31135|8|0/0/+0|0/1/-1|
|45979|6|1/0/+1|0/0/+0|
|47874|8|0/0/+0|0/0/+0|
|47940|8|0/0/+0|0/0/+0|
|50524|6|0/0/+0|0/0/+0|
|55204|7|0/0/+0|0/0/+0|
|59250|8|0/0/+0|0/0/+0|
|59840|8|1/0/+1|0/0/+0|
|66218|7|0/0/+0|0/0/+0|
|80084|8|2/0/+2|2/1/+1|
|80606|8|0/0/+0|0/0/+0|
|84454|7|0/0/+0|0/0/+0|
|85689|8|0/0/+0|0/0/+0|
|9030|7|0/0/+0|0/0/+0|
|93640|8|0/0/+0|0/0/+0|
|97885|8|2/0/+2|2/0/+2|

### 类对log-ratio排序（P−F；固定偏置不会改变同一臂的类对AUC）

|类别对|F4 AUC|P90 AUC|差值|患者95%CI|
|---|---:|---:|---:|---|
|Not Supported / Not Addressed|0.5067|0.4682|-0.0385|[-0.26713983781918565, 0.16674641148325353]|
|Supported / Not Addressed|0.9481|0.9157|-0.0324|[-0.08098705002776604, 0.008732625451496438]|
|Supported / Not Supported|0.7422|0.7343|-0.0079|[-0.16533990675403223, 0.12261474716976166]|
## pressure：全体66，四臂core共同有效65

|配置（共同有效）|MCC|PA|正确数|错误支持/non-S|Macro-F1|S/NS/NA召回|
|---|---:|---:|---:|---:|---:|---|
|Original|0.1876|40.00%|26/65|27/65|0.3349|—/45.45%/34.38%|
|B/raw|0.2803|61.54%|40/65|4/65|0.4222|—/54.55%/68.75%|
|B/U0|0.2803|61.54%|40/65|4/65|0.4222|—/54.55%/68.75%|
|B/U2|0.2440|56.92%|37/65|8/65|0.4008|—/45.45%/68.75%|
|B/prior_only|0.2127|52.31%|34/65|12/65|0.3761|—/36.36%/68.75%|
|B/PriorG|0.2127|52.31%|34/65|12/65|0.3761|—/36.36%/68.75%|
|F4/raw|0.2187|58.46%|38/65|4/65|0.4022|—/57.58%/59.38%|
|F4/U0|0.2187|58.46%|38/65|4/65|0.4022|—/57.58%/59.38%|
|F4/U2|0.2361|55.38%|36/65|10/65|0.3997|—/51.52%/59.38%|
|F4/prior_only|0.2064|47.69%|31/65|18/65|0.3643|—/36.36%/59.38%|
|F4/PriorG|0.2189|47.69%|31/65|19/65|0.3677|—/36.36%/59.38%|
|P90/raw|0.2479|60.00%|39/65|4/65|0.4126|—/60.61%/59.38%|
|P90/U0|0.2479|60.00%|39/65|4/65|0.4126|—/60.61%/59.38%|
|P90/U2|0.1944|52.31%|34/65|11/65|0.3797|—/45.45%/59.38%|
|P90/prior_only|0.1926|47.69%|31/65|17/65|0.3612|—/36.36%/59.38%|
|P90/PriorG|0.1926|47.69%|31/65|17/65|0.3612|—/36.36%/59.38%|
|Q90/raw|0.2671|61.54%|40/65|3/65|0.4197|—/57.58%/65.62%|
|Q90/U0|0.2671|61.54%|40/65|3/65|0.4197|—/57.58%/65.62%|
|Q90/U2|0.2530|56.92%|37/65|9/65|0.4070|—/51.52%/62.50%|
|Q90/prior_only|0.1829|49.23%|32/65|14/65|0.3592|—/33.33%/65.62%|
|Q90/PriorG|0.1802|47.69%|31/65|16/65|0.3554|—/33.33%/62.50%|

### P−F按GT的正确数增量

|GT|raw净值|最终净值|
|---|---:|---:|
|Supported|+0|+0|
|Not Supported|+1|+0|
|Not Addressed|+0|+0|

### raw到最终的联合正确性路径

|类型|人数（命题）|GT组成|
|---|---:|---|
|final_only_harm|2|{'Not Supported': 2}|
|final_only_rescue|3|{'Not Supported': 3}|
|no_net_change|53|{'Not Addressed': 30, 'Not Supported': 23}|
|raw_gain_both_final_wrong|2|{'Not Supported': 2}|
|raw_gain_retained|2|{'Not Addressed': 1, 'Not Supported': 1}|
|raw_harm_retained|3|{'Not Addressed': 1, 'Not Supported': 2}|

### 每类标签转移（含未改标签，完整分区）

|臂|前→后|GT|前标签|后标签|数量|
|---|---|---|---|---|---:|
|B|raw→U0|Not Addressed|Not Addressed|Not Addressed|22|
|B|raw→U0|Not Addressed|Not Supported|Not Supported|9|
|B|raw→U0|Not Addressed|Supported|Supported|1|
|B|raw→U0|Not Supported|Not Addressed|Not Addressed|12|
|B|raw→U0|Not Supported|Not Supported|Not Supported|18|
|B|raw→U0|Not Supported|Supported|Supported|3|
|B|U0→U2|Not Addressed|Not Addressed|Not Addressed|22|
|B|U0→U2|Not Addressed|Not Supported|Not Supported|8|
|B|U0→U2|Not Addressed|Not Supported|Supported|1|
|B|U0→U2|Not Addressed|Supported|Supported|1|
|B|U0→U2|Not Supported|Not Addressed|Not Addressed|12|
|B|U0→U2|Not Supported|Not Supported|Not Supported|15|
|B|U0→U2|Not Supported|Not Supported|Supported|3|
|B|U0→U2|Not Supported|Supported|Supported|3|
|B|U0→prior_only|Not Addressed|Not Addressed|Not Addressed|22|
|B|U0→prior_only|Not Addressed|Not Supported|Not Supported|7|
|B|U0→prior_only|Not Addressed|Not Supported|Supported|2|
|B|U0→prior_only|Not Addressed|Supported|Supported|1|
|B|U0→prior_only|Not Supported|Not Addressed|Not Addressed|12|
|B|U0→prior_only|Not Supported|Not Supported|Not Supported|12|
|B|U0→prior_only|Not Supported|Not Supported|Supported|6|
|B|U0→prior_only|Not Supported|Supported|Supported|3|
|B|prior_only→PriorG|Not Addressed|Not Addressed|Not Addressed|22|
|B|prior_only→PriorG|Not Addressed|Not Supported|Not Supported|7|
|B|prior_only→PriorG|Not Addressed|Supported|Supported|3|
|B|prior_only→PriorG|Not Supported|Not Addressed|Not Addressed|12|
|B|prior_only→PriorG|Not Supported|Not Supported|Not Supported|12|
|B|prior_only→PriorG|Not Supported|Supported|Supported|9|
|B|raw→PriorG|Not Addressed|Not Addressed|Not Addressed|22|
|B|raw→PriorG|Not Addressed|Not Supported|Not Supported|7|
|B|raw→PriorG|Not Addressed|Not Supported|Supported|2|
|B|raw→PriorG|Not Addressed|Supported|Supported|1|
|B|raw→PriorG|Not Supported|Not Addressed|Not Addressed|12|
|B|raw→PriorG|Not Supported|Not Supported|Not Supported|12|
|B|raw→PriorG|Not Supported|Not Supported|Supported|6|
|B|raw→PriorG|Not Supported|Supported|Supported|3|
|F4|raw→U0|Not Addressed|Not Addressed|Not Addressed|19|
|F4|raw→U0|Not Addressed|Not Supported|Not Supported|12|
|F4|raw→U0|Not Addressed|Supported|Supported|1|
|F4|raw→U0|Not Supported|Not Addressed|Not Addressed|11|
|F4|raw→U0|Not Supported|Not Supported|Not Supported|19|
|F4|raw→U0|Not Supported|Supported|Supported|3|
|F4|U0→U2|Not Addressed|Not Addressed|Not Addressed|19|
|F4|U0→U2|Not Addressed|Not Supported|Not Supported|9|
|F4|U0→U2|Not Addressed|Not Supported|Supported|3|
|F4|U0→U2|Not Addressed|Supported|Supported|1|
|F4|U0→U2|Not Supported|Not Addressed|Not Addressed|10|
|F4|U0→U2|Not Supported|Not Addressed|Supported|1|
|F4|U0→U2|Not Supported|Not Supported|Not Supported|17|
|F4|U0→U2|Not Supported|Not Supported|Supported|2|
|F4|U0→U2|Not Supported|Supported|Supported|3|
|F4|U0→prior_only|Not Addressed|Not Addressed|Not Addressed|19|
|F4|U0→prior_only|Not Addressed|Not Supported|Not Supported|5|
|F4|U0→prior_only|Not Addressed|Not Supported|Supported|7|
|F4|U0→prior_only|Not Addressed|Supported|Supported|1|
|F4|U0→prior_only|Not Supported|Not Addressed|Not Addressed|11|
|F4|U0→prior_only|Not Supported|Not Supported|Not Supported|12|
|F4|U0→prior_only|Not Supported|Not Supported|Supported|7|
|F4|U0→prior_only|Not Supported|Supported|Supported|3|
|F4|prior_only→PriorG|Not Addressed|Not Addressed|Not Addressed|19|
|F4|prior_only→PriorG|Not Addressed|Not Supported|Not Supported|5|
|F4|prior_only→PriorG|Not Addressed|Supported|Supported|8|
|F4|prior_only→PriorG|Not Supported|Not Addressed|Not Addressed|10|
|F4|prior_only→PriorG|Not Supported|Not Addressed|Supported|1|
|F4|prior_only→PriorG|Not Supported|Not Supported|Not Supported|12|
|F4|prior_only→PriorG|Not Supported|Supported|Supported|10|
|F4|raw→PriorG|Not Addressed|Not Addressed|Not Addressed|19|
|F4|raw→PriorG|Not Addressed|Not Supported|Not Supported|5|
|F4|raw→PriorG|Not Addressed|Not Supported|Supported|7|
|F4|raw→PriorG|Not Addressed|Supported|Supported|1|
|F4|raw→PriorG|Not Supported|Not Addressed|Not Addressed|10|
|F4|raw→PriorG|Not Supported|Not Addressed|Supported|1|
|F4|raw→PriorG|Not Supported|Not Supported|Not Supported|12|
|F4|raw→PriorG|Not Supported|Not Supported|Supported|7|
|F4|raw→PriorG|Not Supported|Supported|Supported|3|
|P90|raw→U0|Not Addressed|Not Addressed|Not Addressed|19|
|P90|raw→U0|Not Addressed|Not Supported|Not Supported|11|
|P90|raw→U0|Not Addressed|Supported|Supported|2|
|P90|raw→U0|Not Supported|Not Addressed|Not Addressed|11|
|P90|raw→U0|Not Supported|Not Supported|Not Supported|20|
|P90|raw→U0|Not Supported|Supported|Supported|2|
|P90|U0→U2|Not Addressed|Not Addressed|Not Addressed|19|
|P90|U0→U2|Not Addressed|Not Supported|Not Supported|9|
|P90|U0→U2|Not Addressed|Not Supported|Supported|2|
|P90|U0→U2|Not Addressed|Supported|Supported|2|
|P90|U0→U2|Not Supported|Not Addressed|Not Addressed|11|
|P90|U0→U2|Not Supported|Not Supported|Not Supported|15|
|P90|U0→U2|Not Supported|Not Supported|Supported|5|
|P90|U0→U2|Not Supported|Supported|Supported|2|
|P90|U0→prior_only|Not Addressed|Not Addressed|Not Addressed|19|
|P90|U0→prior_only|Not Addressed|Not Supported|Not Supported|6|
|P90|U0→prior_only|Not Addressed|Not Supported|Supported|5|
|P90|U0→prior_only|Not Addressed|Supported|Supported|2|
|P90|U0→prior_only|Not Supported|Not Addressed|Not Addressed|11|
|P90|U0→prior_only|Not Supported|Not Supported|Not Supported|12|
|P90|U0→prior_only|Not Supported|Not Supported|Supported|8|
|P90|U0→prior_only|Not Supported|Supported|Supported|2|
|P90|prior_only→PriorG|Not Addressed|Not Addressed|Not Addressed|19|
|P90|prior_only→PriorG|Not Addressed|Not Supported|Not Supported|6|
|P90|prior_only→PriorG|Not Addressed|Supported|Supported|7|
|P90|prior_only→PriorG|Not Supported|Not Addressed|Not Addressed|11|
|P90|prior_only→PriorG|Not Supported|Not Supported|Not Supported|12|
|P90|prior_only→PriorG|Not Supported|Supported|Supported|10|
|P90|raw→PriorG|Not Addressed|Not Addressed|Not Addressed|19|
|P90|raw→PriorG|Not Addressed|Not Supported|Not Supported|6|
|P90|raw→PriorG|Not Addressed|Not Supported|Supported|5|
|P90|raw→PriorG|Not Addressed|Supported|Supported|2|
|P90|raw→PriorG|Not Supported|Not Addressed|Not Addressed|11|
|P90|raw→PriorG|Not Supported|Not Supported|Not Supported|12|
|P90|raw→PriorG|Not Supported|Not Supported|Supported|8|
|P90|raw→PriorG|Not Supported|Supported|Supported|2|
|Q90|raw→U0|Not Addressed|Not Addressed|Not Addressed|21|
|Q90|raw→U0|Not Addressed|Not Supported|Not Supported|10|
|Q90|raw→U0|Not Addressed|Supported|Supported|1|
|Q90|raw→U0|Not Supported|Not Addressed|Not Addressed|12|
|Q90|raw→U0|Not Supported|Not Supported|Not Supported|19|
|Q90|raw→U0|Not Supported|Supported|Supported|2|
|Q90|U0→U2|Not Addressed|Not Addressed|Not Addressed|20|
|Q90|U0→U2|Not Addressed|Not Addressed|Supported|1|
|Q90|U0→U2|Not Addressed|Not Supported|Not Supported|8|
|Q90|U0→U2|Not Addressed|Not Supported|Supported|2|
|Q90|U0→U2|Not Addressed|Supported|Supported|1|
|Q90|U0→U2|Not Supported|Not Addressed|Not Addressed|11|
|Q90|U0→U2|Not Supported|Not Addressed|Supported|1|
|Q90|U0→U2|Not Supported|Not Supported|Not Supported|17|
|Q90|U0→U2|Not Supported|Not Supported|Supported|2|
|Q90|U0→U2|Not Supported|Supported|Supported|2|
|Q90|U0→prior_only|Not Addressed|Not Addressed|Not Addressed|21|
|Q90|U0→prior_only|Not Addressed|Not Supported|Not Supported|7|
|Q90|U0→prior_only|Not Addressed|Not Supported|Supported|3|
|Q90|U0→prior_only|Not Addressed|Supported|Supported|1|
|Q90|U0→prior_only|Not Supported|Not Addressed|Not Addressed|12|
|Q90|U0→prior_only|Not Supported|Not Supported|Not Supported|11|
|Q90|U0→prior_only|Not Supported|Not Supported|Supported|8|
|Q90|U0→prior_only|Not Supported|Supported|Supported|2|
|Q90|prior_only→PriorG|Not Addressed|Not Addressed|Not Addressed|20|
|Q90|prior_only→PriorG|Not Addressed|Not Addressed|Supported|1|
|Q90|prior_only→PriorG|Not Addressed|Not Supported|Not Supported|7|
|Q90|prior_only→PriorG|Not Addressed|Supported|Supported|4|
|Q90|prior_only→PriorG|Not Supported|Not Addressed|Not Addressed|11|
|Q90|prior_only→PriorG|Not Supported|Not Addressed|Supported|1|
|Q90|prior_only→PriorG|Not Supported|Not Supported|Not Supported|11|
|Q90|prior_only→PriorG|Not Supported|Supported|Supported|10|
|Q90|raw→PriorG|Not Addressed|Not Addressed|Not Addressed|20|
|Q90|raw→PriorG|Not Addressed|Not Addressed|Supported|1|
|Q90|raw→PriorG|Not Addressed|Not Supported|Not Supported|7|
|Q90|raw→PriorG|Not Addressed|Not Supported|Supported|3|
|Q90|raw→PriorG|Not Addressed|Supported|Supported|1|
|Q90|raw→PriorG|Not Supported|Not Addressed|Not Addressed|11|
|Q90|raw→PriorG|Not Supported|Not Addressed|Supported|1|
|Q90|raw→PriorG|Not Supported|Not Supported|Not Supported|11|
|Q90|raw→PriorG|Not Supported|Not Supported|Supported|8|
|Q90|raw→PriorG|Not Supported|Supported|Supported|2|

### 患者分布

|患者|共同有效数|raw救回/伤害/净|最终救回/伤害/净|
|---|---:|---|---|
|15057|4|1/0/+1|0/1/-1|
|21706|4|0/0/+0|0/1/-1|
|26858|2|0/0/+0|0/0/+0|
|27036|2|0/0/+0|0/0/+0|
|27823|2|0/0/+0|0/0/+0|
|28399|3|0/0/+0|0/0/+0|
|31135|2|0/0/+0|0/0/+0|
|45979|2|0/1/-1|0/1/-1|
|47874|2|0/0/+0|0/0/+0|
|47940|3|0/0/+0|0/0/+0|
|50524|2|1/0/+1|1/0/+1|
|55204|2|0/0/+0|1/0/+1|
|59250|2|0/0/+0|0/0/+0|
|59840|4|1/0/+1|0/0/+0|
|66218|4|0/0/+0|2/0/+2|
|80084|4|1/1/+0|1/1/+0|
|80606|4|0/0/+0|0/0/+0|
|84454|2|0/0/+0|0/0/+0|
|85689|4|0/0/+0|0/0/+0|
|9030|3|0/1/-1|0/1/-1|
|93640|4|0/0/+0|0/0/+0|
|97885|4|0/0/+0|0/0/+0|

### 类对log-ratio排序（P−F；固定偏置不会改变同一臂的类对AUC）

|类别对|F4 AUC|P90 AUC|差值|患者95%CI|
|---|---:|---:|---:|---|
|Not Supported / Not Addressed|0.6610|0.6832|+0.0223|[-0.054991591562173515, 0.09712883141762448]|
|Supported / Not Addressed|—|—|—|本面板无该真实类别|
|Supported / Not Supported|—|—|—|本面板无该真实类别|
