# Published-reference + V4 bridge（历史078复用）

复用原192条桥接，TS/RT共同核心有效184条；剔除无效，不沿用旧表fallback。078每患者GT盲hash抽取8条，共24患者。此为历史单独队列，不能冒充096新自然面板，也不是完整Original VeriFact pipeline + V4。

原claim、发布reference不裁剪，使用本研究deepseek-v4-flash-0731 T-S核验提示；与C48＋同T-S比较。精确请求/回执哈希已核对，统计与患者配对区间见cached_published_reference_bridge.json。新增API为0，不部署检索或辅助模型。

旧零API准备中的Original-style不可行说明针对完整原Judge链，本次附件明确允许published-reference桥接，因此直接复用已经合法运行的078，不重复调用。
