# 064 Protocol Amendment 001：Patient-disjoint Future-batch Validation

## 触发原因

主064的R90只作用于052→053 target中的6条claim。

within-batch主评价会把已标注claims从holdout移除，因此当active逐渐标完rescue region后：
- policy认证可能已经获得足够信息；
- 但当前holdout中已没有R90可作用的claim；
- budget越大反而显示“回退BASE”。

这会混淆“policy能否泛化到未来新患者”与“当前小batch里action region已被人工标完”。

本amendment不修改policy library、posterior、风险阈值、budget或active acquisition，只修改评估方式。
## Patient-disjoint calibration / future evaluation

每个target方向固定50个重复。

每个repeat：
1. 仅按sid随机打散，不看GT；
2. 一半患者作为calibration patients；
3. 另一半患者作为future evaluation patients；
4. 0/3/5/10/20个标签只允许从calibration patients中获取；
5. active_policy仍只看policy disagreement与已揭示标签；
6. 选定policy后，直接应用到future patients全部claims；
7. future GT只用于最终评价。

若calibration disagreement region不足budget，active允许少用标签，不强行标policy一致claim。
random_global仍从calibration全部claims patient-diverse随机抽取。
## Oracle与成功标准

Oracle policy仍沿用主064对完整target环境的诊断：
- 052→053：由完整GT决定；
- 053→052：由完整GT决定。

不使用future fold GT重新选择oracle。

每个budget汇总：
- oracle match；
- unsafe switch；
- beneficial nonBASE selection；
- BASE fallback；
- future ΔPA / ΔMCC / Δfalse-S / ΔNS / ΔNA；
- 实际使用标签数。

“missing link closed”标准完全沿用主064：
- unsafe-switch <=10%；
- oracle nonBASE方向：safe beneficial nonBASE selection >=70%；
- oracle BASE方向：BASE fallback >=90%；
- mean future ΔPA/MCC >=0；
- mean future ΔNS/NA >=-0.02。

结果单独保存，不覆盖主064。
## 边界

- 这是同一target development pool内的patient-disjoint模拟，不是外部医院验证。
- 同一claim不会同时出现在calibration与future fold。
- 0 API，不使用reserved，不自动commit/push。
