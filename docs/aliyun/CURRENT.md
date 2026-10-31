# 当前Judge配置（2026-10-31维护）

## 已启用的默认方式

用户已授权将通过测试的新端点及Key用于后续调用，根目录.env.aliyun已更新：

| 配置 | 当前值 |
|---|---|
| DASHSCOPE_BASE_URL | https://maas.qianwenaiapi.com/compatible-mode/v1 |
| DASHSCOPE_MODEL | deepseek-v4-flash-0731 |
| DASHSCOPE_API_KEY | 仅保存于本地.env.aliyun，不在文档展示 |
| 通用思考默认 | enable_thinking=true、reasoning_effort=high |

客户端默认值和无密钥模板同步；正式研究的prompt、输出上限、格式契约、队列与费用仍按任务冻结。此次更换接入配置不是默认研究方法升级，也不将测试用200条库存记录或2048输出上限用于临床实验。

load_config只读取指定文件，环境变量不覆盖它；运行中的客户端不会自动刷新。原配置保存在受忽略的.env.aliyun.before_qianwen_20261026；测试配置.env.aliyun.qianwen_test仅作私有留档，后续正常使用主配置，无需再指定测试文件。三个文件均已确认被Git忽略。

## 实际测试证据

| 时间／配置 | 结果 |
|---|---|
| 2026-10-25旧端点，三模型 | 403 AccessDenied.Unpurchased，保留历史失败记录 |
| 2026-10-26新端点，V4非思考极简请求 | HTTP200，回答OK.，输入9／输出2 tokens，估算¥0.000045 |
| 2026-10-26新端点，V4 thinking-high合成库存JSON请求 | HTTP200，输入6571／输出288 tokens（109推理tokens），返回verdict、checks和三分数；估算¥0.022305 |
| 2026-10-31 21:14，默认V4 thinking-high极简请求 | HTTP200，返回OK，输入88／输出8 tokens（6推理tokens），请求耗时2.51秒，按忙时原价估算¥0.000336；0重试、未发送临床数据 |

成功调用均无重试、未发送患者数据。价格按输入3／输出9元每百万token保守估算，不是已核账单；连接检查累计保留¥0.159494未知／未对账预留，启用主配置不清零。此次默认切换只做离线检查，未追加成功调用。

上述结果证明端点、账号及所测思考/JSON请求可用；没有验证冻结临床prompt的逐字段契约、并发、数值稳定性或跨平台科学等价。合成测试中checks返回列表，不能直接据此宣称完整T-S协议已通过。

私有测试台账位于outputs/replays/qianwen_connection_20261026T081723258799Z/及outputs/replays/qianwen_thinking_smoke_20261026T083326959560Z/。历史资料不因启用配置改写。

## 费用与恢复

新任务默认总上限20元，专项授权优先；预检、重试、未知和在途预留共同累计。成功回答不因内容不好重发；普通网络故障有限恢复，持续鉴权或模型条件异常停止相关发送。详见[API政策](../API_POLICY.md)。

AliyunClient.send是单次传输层，不自动重试。旧CLI/call_once默认40元是历史代码保护值，新任务显式传通常20元的有效上限。不能仅换Key就把旧任务的累计费用归零。

[官方Key与端点说明](https://platform.qianwenai.com/docs/api-reference/preparation/api-key) · [无密钥模板](config.env.example)

2026-10-31该次连接测试的私有回执在.local_models/api_connection/aliyun_20261031T131437828001Z/，保留¥0.05未对账预留，连接测试累计预留¥0.209494；不无据清除原¥0.159494。随后新授权的夜间研究API单独按PROJECT_STATUS专项累计，实际请求在.local_models/night_20261031/api_ledger.jsonl登记；连接测试旧账不冒充新研究零成本。
