"""Current pointers only:096 is READY, not a completed scientific experiment."""
import common096 as c
def update(name,fn):
    p=c.ROOT/name;data=p.read_bytes();bom=data.startswith(b'\xef\xbb\xbf');s=data.decode('utf-8-sig' if bom else 'utf-8');nl='\r\n' if '\r\n' in s else '\n';new=fn(s.replace('\r\n','\n'))
    p.write_bytes((b'\xef\xbb\xbf' if bom else b'')+new.replace('\n',nl).encode('utf-8'))
def main():
    note='096 R1原生比较与同配方PriorG适配已完成零API准备，状态READY_FOR_R1；143校准＋800主＋200压力请求冻结，未访问R1或收费API，等待用户服务与预算信息。旧096构造修复已停止且不恢复，默认仍V4-B＋Frozen PriorG。'
    update('AGENTS.md',lambda s:s.replace('## 当前状态与数据授权\n\n','## 当前状态与数据授权\n\n- '+note+' [准备报告](outputs/096_r1_native_priorg/report_preparation.md) · [恢复入口](tasks/096_r1_native_priorg/README.md)。\n',1))
    update('README.md',lambda s:s.replace('## 当前结论与入口\n\n','## 当前结论与入口\n\n'+note+' [096准备报告](outputs/096_r1_native_priorg/report_preparation.md)。\n\n',1))
    update('docs/PROJECT_STATUS.md',lambda s:s.replace('## 最近结果与可主张范围\n\n','## 最近结果与可主张范围\n\n'+note+' 当前准备HEAD为`28daf95e9b12270d8089246176023c66c4cf298e`；此状态不是完整096已完成，也不继承095的150元额度。[准备报告](../outputs/096_r1_native_priorg/report_preparation.md)。\n\n',1))
    update('docs/TASK_INDEX.md',lambda s:s.replace('（截至095）','（截至096零API准备）',1).replace('|095_anchored_minimal_contrast|','|096_r1_native_priorg|[零API准备报告](../outputs/096_r1_native_priorg/report_preparation.md)|独立审计未执行；[离线自检](../outputs/096_r1_native_priorg/offline_selfcheck.json)|READY_FOR_R1，等待服务/预算，不恢复旧096构造；无新推理成绩|\n|095_anchored_minimal_contrast|',1))
    update('docs/API_POLICY.md',lambda s:s.replace('## 路由\n\n','096当前仅获零API准备授权，R1端点探测和收费发送均未授权启动。GPU30元／按token10元只是运行提示中的建议，需用户服务就绪时确认；不继承旧096或095额度、不猜余额。费用与恢复入口见[096准备](../tasks/096_r1_native_priorg/README.md)。\n\n## 路由\n\n',1))
    print('Current navigation marks096 READY, not scientific completion')
if __name__=='__main__':main()
