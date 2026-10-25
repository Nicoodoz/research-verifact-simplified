# 090 价格与JSON接口核对

本轮采用既有阿里云北京快照。发送前沿同日已核对官方费率登记；跨午夜2026-09-27再次检索官方页面，费率与冻结账本一致，没有改预算或增加样本。

- [DeepSeek V4 Flash 0731官方价格](https://help.aliyun.com/zh/model-studio/deepseek-v4-flash)：按忙时、非缓存输入3元/输出9元每百万token计。未用闲时与缓存折扣扩大40元额度。
- [Qwen3.5 Flash官方页面](https://help.aliyun.com/zh/model-studio/qwen3-5-flash)及[官方价格表](https://help.aliyun.com/zh/model-studio/model-pricing)：2026-02-23快照在≤128k输入档按0.2元/输出2元每百万token。执行器对请求UTF8字节保守上界检查价档。
- [官方结构化输出说明](https://help.aliyun.com/zh/model-studio/qwen-structured-output)：JSON Object仅保证JSON格式，不保证特定字段结构；严格Schema只支持列明的部分模型。090没有假设Qwen3.5 Flash支持严格schema，也没有为此换模型，使用简化接口、短完整示例和本地确定性归一。

部分直接页面读取曾超时，官方搜索结果可取得对应快照价表；不将网页读取失败当作模型推理失败，也没有因此多发主Judge请求。实际原价由回执usage与上述费率计算，非平台账单对账。
