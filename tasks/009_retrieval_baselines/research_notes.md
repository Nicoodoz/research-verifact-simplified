# 009：实现核对与论文定位底稿

本轮按 academic-paper-reading 的问题—方法—证据—限制检查法定向核对，没有声称完成系统综述。以下均为原作者代码或官方文档；公共页面于 2026-09-15 核对。

|来源与实际阅读范围|本轮确认的相关设置|对009的含义|
|---|---|---|
|VeriFact 固定 f115d36 的 `reference_context.py`：构造器、检索模式、去重/重排/截取；`qdrant.py` 默认融合设置；`m3_embedding.py` 和 `m3_reranker.py` API包装，已在007保存|作者BGE embedding默认同时请求dense和learned sparse；Qdrant默认distribution-based score fusion；重排使用原query，随后取top_n；不是本项目手写BM25＋RRF|A是当前本地baseline，不能叫“精确原作者复现”。保留可复现替代实现，明确API/切分/过滤差别即可回答本任务|
|[BGE-M3官方模型卡](https://huggingface.co/BAAI/bge-m3)：功能、规格、FAQ和dense/sparse使用代码|dense1024维、最长8192；query不需要额外instruction；learned sparse输出token权重，区别于BM25|本API只用dense，BM25在本地另算；不能把两者混称。官方推荐hybrid＋rerank不保证任意融合/截取在本任务必胜|
|[BGE reranker官方模型卡](https://huggingface.co/BAAI/bge-reranker-v2-m3)：模型描述和compute_score示例|逐query/passage产生相关分数，可用sigmoid转为0–1；不是候选间softmax，更不是支持关系概率|相同query/document和设置的旧配对可缓存，另查跨日分数漂移；无重排条件用实际dense分数，不填假rerank值|
|[硅基流动官方更新](https://docs.siliconflow.cn/docs/release-notes/overview)及[价格](https://siliconflow.cn/pricing)|V4 Flash按2026-09-01起输入3/缓存.3/输出9元每百万及夜间半价；BGE两种Pro输入.07元每百万。9-15起repetition_penalty被忽略，本轮请求未设置该参数|记录日期单价，仍不是账单或不可变服务版本；严格任务40元总保护，不调用已停用user/info接口|

固定代码来源：[作者 reference_context.py](https://github.com/philipchung/verifact/blob/f115d36cb65fa2073fce0a10df56bb37f4cbcd50/packages/llm_judge/src/llm_judge/reference_context.py)。本地原文及哈希见 `docs/sources/007_context_retrieval/manifest.json`；BGE说明与008已有文献材料也继续保留。

相关工作定位沿用008已经读到的方法原文：Query2doc与Query Rewriting研究生成式扩展/改写；RARR生成核验问题寻找证据；Step-by-Step FV已应用医学公开声明，但与个人EHR、原独立命题医生标签和NA类别并不相同。009的贡献候选不能是“换成dense”“换融合公式”或“修空白解析”本身，而应由受控结果回答：证据在检索链条何处丢失、哪些基础控制足以解释此前扩展收益、哪些判断误差在证据改善后仍保留。新确认结果尚未生成前不写已验证优势。
