# 来源、构造覆盖与失败台账

四例主构造与额外候选覆盖分开；模型生成的信息清单不是医生GT。

|槽位|臂|状态|原字符|最终字符|初选ID|补回ID|最终ID|
|---|---|---|---:|---:|---|---|---|
|1|P4|short_or_single_unit|745|745|U001||U001|
|1|Q4|short_or_single_unit|745|745|U001||U001|
|2|P4|invalid_constructor_full_retention|8013|8013|U001,U002,U003,U004,U005,U006,U007,U008,U009,U010,U011||U001,U002,U003,U004,U005,U006,U007,U008,U009,U010,U011|
|2|Q4|constructed|8013|4253|U001,U002,U003,U007,U008,U009||U001,U002,U003,U007,U008,U009|
|3|P4|short_or_single_unit|754|754|U001||U001|
|3|Q4|short_or_single_unit|754|754|U001||U001|
|4|P4|invalid_constructor_full_retention|7961|7961|U001,U002,U003,U004,U005,U006,U007,U008,U009,U010,U011||U001,U002,U003,U004,U005,U006,U007,U008,U009,U010,U011|
|4|Q4|invalid_constructor_full_retention|7961|7961|U001,U002,U003,U004,U005,U006,U007,U008,U009,U010,U011||U001,U002,U003,U004,U005,U006,U007,U008,U009,U010,U011|

## 其余8条D候选：不用于替换F4或目标评价

|候选|臂|状态|原字符|最终字符|初选/最终段数|补回段|
|---|---|---|---:|---:|---|---|
|C05|P4|invalid_constructor_full_retention|8160|8160|11/11||
|C05|Q4|constructed|8160|5433|5/7|U001,U002|
|C06|P4|constructed|8153|916|1/1||
|C06|Q4|constructed|8153|4605|6/6||
|C07|P4|invalid_constructor_full_retention|8155|8155|13/13||
|C07|Q4|constructed|8155|4663|5/6|U013|
|C08|P4|constructed|8069|4118|6/6||
|C08|Q4|constructed|8069|3927|5/5||
|C09|P4|invalid_constructor_full_retention|8133|8133|13/13||
|C09|Q4|constructed|8133|5421|5/7|U001,U003|
|C10|P4|invalid_constructor_full_retention|7631|7631|10/10||
|C10|Q4|constructed|7631|3893|5/5||
|C11|P4|invalid_constructor_full_retention|8159|8159|13/13||
|C11|Q4|constructed|8159|4244|6/6||
|C12|P4|invalid_constructor_full_retention|8002|8002|11/11||
|C12|Q4|invalid_constructor_full_retention|8002|8002|11/11||

完整模型回答、逐引文的接受/拒绝理由见construction/与coverage/。短/单单元不调用；所有长槽P/Q独立调用，不做目标性能选例。
