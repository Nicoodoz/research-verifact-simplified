# 121 nearest_memory：已完成，停止扩大

用缓存107无答案表示做32人记忆库/8人内部验证的6配置kNN筛查，固定选k=31均匀投票。160上自然正确+13但false-S+5，压力正确−2且false-S+5；不扩大500，不改变107基线。

代码：[nearest_memory121.py](nearest_memory121.py)。[完整结果](../../outputs/121_nearest_memory/report.md)。新增GPU/API均为0；近邻和记忆向量保存在私有目录。
