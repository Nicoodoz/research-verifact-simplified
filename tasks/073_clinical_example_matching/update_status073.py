"""Update mutable navigation only; preserve each file's encoding and line endings."""
from materials073 import ROOT,OUT,read
def rewrite(path,transform):
 raw=path.read_bytes();bom=raw.startswith(b'\xef\xbb\xbf');text=raw.decode('utf-8-sig');nl='\r\n' if b'\r\n' in raw else '\n'
 new=transform(text.replace('\r\n','\n')).replace('\n',nl).encode('utf-8')
 path.write_bytes((b'\xef\xbb\xbf' if bom else b'')+new)
def main():
 p=read(OUT/'pilot_analysis.json');v=read(OUT/'verification.json');c=read(OUT/'conclusion.json')
 a=read(OUT/'confirmation_analysis.json') if (OUT/'confirmation_analysis.json').exists() else None
 core='073已完成：新命题36条探索B/F4/D4/L4/M4正确31/33/30/31/31；修正词汇和缓存BGE语义匹配未超过静态F4，按事前规则停止动态版本。F4探索净+2含1条输出截断后的历史U2回退，不能全部归功于示例。'
 if a:
  b,f=a['final_metrics']['B'],a['final_metrics']['F4'];p0=a['final_pairs']['F4_minus_B']
  core+=f'另10人60条开发确认B/F4正确{b["correct"]}/{f["correct"]}，MCC {b["MCC"]:.4f}/{f["MCC"]:.4f}，净{p0["net"]:+}，false-S变化{p0["delta_falseS"]:+}；'
  core+=('保留有限静态开发信号，默认仍B。' if c['confirmation_gates']['F4']['pass_gate'] else '未达确认门槛，默认仍B。')
 core+=f'累计估算¥{v["cost_cny"]:.6f}/20，{v["answers"]}个成功回答、成功同体不重复；自检PASS，独立审计未执行，不自动074、不提交推送。'
 for name,link in [('README.md','outputs/073_clinical_example_matching/report.md'),('docs/PROJECT_STATUS.md','../outputs/073_clinical_example_matching/report.md')]:
  def change(t):
   t=t.replace('## 现行摘要（2026-09-23，072结项后）','## 现行摘要（2026-09-24，073结项后）',1)
   marker='## 现行摘要（2026-09-24，073结项后）\n\n'
   assert marker in t and '**073临床教学示例匹配：**' not in t
   return t.replace(marker,marker+'- **073临床教学示例匹配：** '+core+f'[073报告]({link})。\n',1)
  rewrite(ROOT/name,change)
 def agents(t):
  t=t.replace('## 现行工作约定（2026-09-23，优先于下方阶段快照）','## 现行工作约定（2026-09-24，优先于下方阶段快照）',1)
  marker='## 现行工作约定（2026-09-24，优先于下方阶段快照）\n\n'
  t=t.replace(marker,marker+'- **073最新：** '+core+'[073报告](outputs/073_clinical_example_matching/report.md)。\n',1)
  t=t.replace('072用户专项上限30元、已用估算¥12.971532；不改`.gitignore`、不使用reserved、不自动073。本轮用户明确授权完成072后提交并推送GitHub。','072历史专项上限30元、估算¥12.971532，其提交推送授权仅适用072。073由用户新交办，20元上限；不改`.gitignore`、不使用reserved、不自动074、不提交推送。',1)
  return t
 rewrite(ROOT/'AGENTS.md',agents)
 rewrite(ROOT/'docs/RESEARCH_EXECUTION.md',lambda t:t.replace('不自动启动073。当前结果见','073已由用户另行交办并完成，动态匹配未通过探索筛选；结果及静态确认见073报告，不自动启动074。当前结果见'))
 for folder in [OUT,ROOT/'tasks/073_clinical_example_matching']:
  link='report.md' if folder==OUT else '../../outputs/073_clinical_example_matching/report.md'
  (folder/'CURRENT_STATUS.md').write_text('# 073 当前状态\n\n'+core+f'\n\n[完整报告]({link})。\n',encoding='utf-8',newline='\n')
 (OUT/'README.md').write_text('# 073 结果入口\n\n'+core+'\n\n[正式报告](report.md) · [逐例诊断](pilot_case_notes.md) · [费用](cost_ledger.json) · [自检](verification.json) · [事前协议](../../tasks/073_clinical_example_matching/README.md)\n',encoding='utf-8',newline='\n')
 print(core)
if __name__=='__main__':main()
