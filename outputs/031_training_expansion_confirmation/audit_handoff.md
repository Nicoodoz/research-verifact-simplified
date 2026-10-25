# 031 独立审计交接

## 状态

执行者已完成031，[主报告](report.md)和[CURRENT_STATUS](CURRENT_STATUS.md)为现行入口；**尚未独立审计，不宣布PASS**。基准HEAD为`6f7b566b`（完整值在handoff_001/manifest.json），新增代码、成果和四份导航未提交，未推送。

没有确认扩大训练带来实质改善；after C−A、D−B在实际工作点对参考完整随机混合曲线分别−3.50/−5.14R。保留A简单参照，停止当前新增信息Gate；不改阈值、不用reserved40或启动032。

## 输入、冻结与顺序

- [protocol_001](protocol_001.md)、[planning_001](planning_001/manifest.json)：003身份、原16/扩充12/确认12、metadata-only划分及输入指纹。
- [materials_001](materials_001/manifest.json)：745条旧C48验证缓存、1401条原API-BGE新构造、原raw/冻结向量来源。raw查询逻辑只保留24名development；CSV解压扫描不应写成物理未读取全文件字节。
- [freeze_001](freeze_001/manifest.json)、[执行冻结](execution_freeze_001.json)、[评价冻结](analysis_contract_001.json)：科学配方和代码在新Judge结果前固定，旧科学源码字节未改。
- [before_models](before_models/manifest.json)早于首次031API；[inference_001](inference_001/manifest.json)保存八模型及确认盲预测，其后才逻辑读取确认GT，时序见[连接记录](analysis_001/GT_connection.json)。日志/哈希不是外部可信时间戳。
- 训练原155/R110，扩充91/R67，确认124/R92；所有四方案共用完整训练候选。无候选原患者15057仍保留在分组和完整队列。
- [candidate_freeze_001](candidate_freeze_001/summary.json)：2146主score核心有效，GT盲生成215候选；Qwen/repeat/trace各215。确认1148/1148完整，非核心异常保留，零核心缺失或回退。
- `attempts/*/request.json`及`receipt.json`包含原生请求、响应与绑定；无GT/作者/旧答案输入，成功200不重跑。Qwen仅候选；repeat/trace均DeepSeek0731，max4096与主评分max2048分别保持。

## 保留的异常和操作修订

1. account_2最初4个401；用户明确授权031暂时使用下一启用账号，见account_override_001及manifest。不是余额耗尽，不修改长期规则。
2. 14个BGE429 TPM失败，按冻结无200最多三次规则重试；pacing_amendment_001增加发送间隔，不改payload。
3. 主score保存894成功后Windows进度文件替换失败；11个在途请求无回执。io_amendment_001保留原status/tmp、合成复现和未知清单；safe_io031只给原writer增加重试及非核心进度写入降级。未知均保留费用上界，后续仅补未保存200的请求。
4. direct env python的SciPy原生启动失败发生于API前，改用conda run激活正确DLL路径；不改学习参数。仅隔离029补duckdb/绘图依赖，主环境未改。
5. 首版粗预算和最终发送前预算均保留。累计37.70924338/80元含失败/未知预留约0.73094568元，非账单；费用不因账号、重启、角色或组别重置。

操作修订均早于确认评价，不依据成绩修答案。figures_001保留首次渲染，figures_002仅删除重叠文字标记，统计输入一致；报告使用002。

## 评价边界

[analysis_001](analysis_001/manifest.json)保留八模型、U0/U2、002指标、作者分层、混淆矩阵、患者、逐条修错误伤、全概率阈值、完整global-λ及同risk/同R参照。两主要比较C−A、D−B共用1000患者重采样，给95%及Bonferroni两比较97.5%区间；固定预测、不重新训练。辅助区间不是全面多重检验保证。

随机混合包络是GT知情期望参照，不可部署；不从确认曲线选阈值。训练内80% R目标不是测试或临床安全保证。H/W分开，不能将W变化等同正确数变化。LLM真实S占93.80%、NA仅9条，不能只看PA。全为曾暴露development；旧新服务时间差异不作纯人数因果解释。

## 安全离线复查

仓库根目录，隔离环境，指定尚不存在的输出目录：

```powershell
E:/miniconda3/Scripts/conda.exe run --no-capture-output -n research-verifact-029 python -u -B tasks/031_training_expansion_confirmation/offline_verify031.py --output verification_audit_001
```

入口禁止socket网络，读已有回执和模型，**0 API、0拟合、不覆盖历史目录**。核对分组、预算/绑定、无重复200、C48候选与打包、029特征、176个保存模型状态的scaler/概率/内层阈值、完整确认动作、002指标、独立混淆计数和同风险LP。执行者25733项通过，见verification_001；不是独立审计，也没有从原raw重算全部检索排名或重新拟合全部模型。

如需复算评价，使用`analyze031.py --output analysis_audit_001`的新目录；已有八模型及盲预测指纹先校验，再连接已获准确认GT，无API或拟合。日常复查不要运行准备/冻结/API workflow入口。

事前test031.py五项和test_analysis031.py四项已通过：身份、预算、输入白名单、旧155条特征复现、患者隔离、缺失回退保持U0、主要区间修正；结果登记在冻结记录。统一评价复用002，未另造指标或改主环境。

## 指纹与建议审计重点

[handoff_001/manifest.json](handoff_001/manifest.json)绑定所有031源码、请求回执、准备、模型、分析、报告、图表及失败现场，同时保存四份导航指纹。`frozen_dependencies.json`核对原输入和预注册代码；.gitignore、API_POLICY、主环境及历史成果无tracked修改。

建议优先核对GT连接顺序、训练内患者边界、三角色真实body及特征、未知请求预留、完整global混合上界和两主要负向比较，以及“停止当前版本”与“证明信息永远无效”的区分。交审后停止改动同批成果，等待独立意见。
