# AWQ → AWQ-Marlin

仅因用户核实部署kernel速度异常而切换，未读取旧P0/P1准确率。旧runner后台PID30956已停止，旧锁和所有工件保留。

旧P0 HTTP200：1；旧P1 HTTP200：0；未完成attempt：2；unknown：2；已保存response：1。

旧AWQ所有输出均AWQ_DIAGNOSTIC_ONLY，不用于R1评价或拟合，不补跑旧unknown。新backend请求ID包含backend身份，同命题旧成功不阻止新backend首次调用；新backend内部HTTP200禁止重发。

样本、GT比例、校准监督、claim/C48和科学请求body不变。manifest的kernel由用户提供，/models只独立证明served model与context，不伪称远程权重/kernel逐字节验证。
