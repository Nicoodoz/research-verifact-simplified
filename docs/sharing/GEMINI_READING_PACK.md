# GitHub阅读副本与Gemini材料（2026-10-26）

日常阅读使用[research-verifact-simplified](https://github.com/Nicoodoz/research-verifact-simplified)，其outputs只保留关键成果；[research-verifact](https://github.com/Nicoodoz/research-verifact)保留全部允许发布的outputs成果用于归档。用户只说“推送到GitHub”时，由执行模型同时更新两个仓库，其他文件使用同一快照，并分别核验发布结果，用户无需维护脚本。未收到推送指令时，本地修改不会自动同步。

## 已发布版本

| 仓库／版本 | 范围 |
|---|---|
| research-verifact，1111a3e | 完整研究仓库，当前提交快照约6.19 GB；不因精简副本维护而删除本地历史材料 |
| research-verifact-simplified，21d6a95 | 2026-10-26发布快照约42.73 MB／2543文件；outputs保留254个关键文档与说明，其他2289个文件与当时本地允许同步范围逐字节一致 |
| research-verifact-simplified-simplified，acd02ce | 更短的历史阅读快照，7个Markdown、约55 KB；不是自动更新的当前代码仓库 |

这些是固定发布版本统计，不是持续变化工作区的实时大小。现在的本地文档更新尚未包含在上述提交中。输出压缩保留各任务报告、重要表格和更正，删除的是副本中的批量中间产物；原项目与历史提交仍可回查。

## 给网页模型阅读

如网页端不能读取仓库，可自行通过GitIngest等工具把精简仓库转换为文本再上传。体积限制、token上限和网页权限以实际账号为准；本文不承诺某个服务能直接导入或完整读取。较短副本适合快速了解研究，精简仓库适合核对代码和报告。

## 与旧导出工具的区别

`build_gemini_reading_pack.py`和`build_gemini_mirror.py`是2026-10-25旧方案，曾生成0.74 MB八文件包和选择性脱敏镜像；它们会筛选或改写outputs之外的材料，不能直接当作当前“其他文件保持一致”的发布入口。旧目录在outputs/replays中保留，本页不再推荐重新运行它们覆盖现行副本。

当前同步必须在独立精简仓库工作副本中完成，不改主仓库origin；保留允许公开的代码和说明，逐项检查私有内容，排除data、凭据、私有回执、权重和缓存。精简版不是完整复现包，报告中的历史机器附件链接可能需要回完整仓库查看。规则以[AGENTS](../../AGENTS.md)为准。
