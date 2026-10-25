"""Maintain current live entry points; preserve all prior preparation snapshots."""
import common096 as c
from live_run096 import O,P
def main():
    status='096已按用户最新服务就绪授权进入R1跨Judge比较：新自然800/600/400嵌套面板和NS/NA诊断面板冻结，沿用051同143校准；先P0及并发benchmark，再仅按速度选择Tier。默认V4-B＋Frozen PriorG不变，旧096构造修复不恢复。'
    if not (O/'service_manifest.json').exists():
        c.put(O/'service_manifest.json',dict(model=c.MODEL,base_url='http://127.0.0.1:18000/v1',observed_models_HTTP=200,observed_root='/root/autodl-tmp/models/models/Valdemardi--DeepSeek-R1-Distill-Llama-70B-AWQ/snapshots/master',observed_max_model_len=20000,user_attested=dict(GPU='NVIDIA A800 80GB PCIe',vllm='0.10.1.1',quantization='AWQ4bit',download_provider='ModelScope',reasoning_parser='deepseek_r1'),immutable_revision=None,server_full_command=None,remote_weight_bytes_verified=False,local_tokenizer_source=c.read(c.OUT/'tokenizer_manifest.json'),billing_hourly_price=None,billing_start=None,initial_probe_note='Unauthenticated GET401; authenticated Bearer EMPTY GET200. No inference retry involved.',authorization='latest full user attachment; time-based existing-instance run; no cloud purchases',source_attachment_sha256=c.sha(c.Path('C:/Users/13359/.codex/attachments/a6970812-bd0e-48bb-8786-bb8af45d8306/已粘贴的文本.txt'))))
    old='096 R1原生比较与同配方PriorG适配已完成零API准备，状态READY_FOR_R1；143校准＋800主＋200压力请求冻结，未访问R1或收费API，等待用户服务与预算信息。旧096构造修复已停止且不恢复，默认仍V4-B＋Frozen PriorG。'
    for name in ['AGENTS.md','docs/PROJECT_STATUS.md','README.md','docs/TASK_INDEX.md']:
        path=c.ROOT/name;data=path.read_bytes();s=data.decode('utf-8');s=s.replace(old,status);path.write_bytes(s.encode('utf-8'))
    path=c.ROOT/'docs/API_POLICY.md';s=path.read_bytes().decode('utf-8');oldp='096当前仅获零API准备授权，R1端点探测和收费发送均未授权启动。GPU30元／按token10元只是运行提示中的建议，需用户服务就绪时确认；不继承旧096或095额度、不猜余额。费用与恢复入口见[096准备](../tasks/096_r1_native_priorg/README.md)。'
    s=s.replace(oldp,'096最新用户已授权现有AutoDL服务的P0、并发benchmark及按剩余3.5/4小时时限选择的R1规模；此前零API暂停已解除。实例小时价/完整账单未知，GPU单独记录墙钟，不把旧GPU30/API10建议当已确认额度；不继承095额度、不猜余额、不租新资源。当前按token新调用0，优先复用桥接缓存。[现场协议与恢复](../tasks/096_r1_native_priorg/LIVE_README.md)。');path.write_bytes(s.encode('utf-8'))
    c.write(c.OUT/'CURRENT_STATUS.md',status+'\n\n现场状态和进度见live_v1；report_preparation.md及READY_FOR_R1.json为旧零API快照，不代表当前执行状态。')
    c.write(c.TASK/'LIVE_README.md','''# 096现场执行与恢复

最新入口，替代README旧零API等待步骤；原准备文件原样保留。主协议：outputs/096_r1_native_priorg/live_v1/protocol.md。

```powershell
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/live_run096.py status
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/live_run096.py benchmark --execute
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/live_run096.py formal --execute
pwsh -File scripts/run_research.ps1 tasks/096_r1_native_priorg/live_analyze096.py
```

benchmark完成后冻结tier，formal不再选样。P0/稳定性失败不继续formal，RUNTIME_TOO_HIGH等待用户。HTTP200位置始终复用，包括invalid。正式完成会立即打印R1_INFERENCE_DONE及对账路径；此时可在AutoDL平台关闭实例，之后所有拟合/统计离线。status不探测网络。省略--execute只dry-run。

进程中断：先确认没有本任务进程仍活动，不盲删run.lock；未取得回执的请求按未知在途，必须服务metrics确认idle才能有限恢复。进程安全退出会清锁，强杀留下锁时人工核对PID。若超冻结4小时停止发送，不自动重置时间窗口。

所有临床请求/原始响应在.local_models/096_r1_native_priorg/live_v1，公开只保存ID/标签/哈希/用量。新token API未开启，GPU租金因小时价和计费起点未知暂不填金额。此轮不改变默认，不恢复旧构造任务。
''')
    c.put(O/'execution_code_freeze.json',dict(utc=c.now(),files={p.name:c.sha(p) for p in c.TASK.glob('live_*096.py')},scientific_requests_frozen_before_first_send=True,old_offline_code_unchanged=True))
if __name__=='__main__':main()
