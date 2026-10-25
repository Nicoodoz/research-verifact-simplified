"""Finalize continuation notes after machine checks; no scientific recomputation."""
import sys, json, subprocess, importlib.metadata as md
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'tasks/032_evidence_relation_correction'))
import common032 as c

def main():
    close = c.read(c.OUT / 'closeout_001/checks.json')
    replay = c.read(c.OUT / 'verification_001/checks.json')
    extra = c.read(c.OUT / 'verification_supplementary_001/summary.json')
    c.require(close['passed'] and replay['passed'] and extra['passed'], 'Cannot finalize failed checks')
    manifest = c.read(c.OUT / 'nli_001/manifest.json')
    status = ['# 032 当前状态', '', '执行、确认评价及执行者自检完成；尚未独立审计。', '',
              '主报告：report.md；正式评价：analysis_001；确认盲预测：inference_001/predictions_blind.jsonl。',
              '28名已暴露development患者用于训练，另12名作开发确认；没有使用reserved40。',
              '全部3675条主张、54236个不同NLI配对已完成；零新增付费API，未改主环境或029环境。',
              '预先规定的五个模型家族全部完成训练侧选择；不从确认成绩改参数或选种子。',
              'verification_001为保存模型重放；verification_supplementary_001为缓存/模型/隔离/选择检查。',
              '工程续跑与批量调整见engineering_001/resume_002.md。',
              '不自动033、reserved测试、commit或push。']
    c.text(c.OUT / 'CURRENT_STATUS.md', '\n'.join(status) + '\n')
    c.text(c.TASK / 'CURRENT_STATUS.md', '# 032当前状态\n\n见 ../../outputs/032_evidence_relation_correction/CURRENT_STATUS.md。\n执行者自检完成，尚未独立审计，不自动后续任务。\n')
    env = {p: md.version(p) for p in ['torch', 'transformers', 'numpy', 'scipy', 'pandas', 'scikit-learn', 'safetensors']}
    c.put(c.OUT / 'engineering_001/environment_after.json', dict(python=sys.version, executable=sys.executable, versions=env))
    handoff = ['# 032 独立审计交接', '', '**执行与执行者自检完成；不宣称独立审计PASS。**', '',
               '## 研究范围',
               '主报告为report.md。沿031的28/12患者边界；原claim、C48、DeepSeek评分不变，确认患者早已暴露，不能称全新最终测试。',
               '冻结DeBERTa NLI，使用真实片段和同note已选片段两粒度。NLI标签不直接等同医生标签。只训练聚合/残差头。',
               '五家族、两个隐藏宽度、三个预定种子和四个修正系数；全部选择仅基于28训练患者的四折预测。种子平均，不挑确认最好种子。',
               '## 冻结和结果',
               'preparation_001：输入、仅训练标签、031划分、四折、配置及环境。',
               'model_manifest.json：公开模型固定revision及全部模型文件哈希；没有上传临床数据。',
               'nli_001：窗口映射、来源绑定、配对数量及大缓存指纹；大缓存位于.local_models/032。',
               'training_001：所有内层配置成绩、各折模型、仅训练侧选择和冻结；这些是选模型资料，不是独立确认成绩。',
               'inference_001：固定选择后的模型与确认盲预测；analysis_001/GT_connection.json记录后续标签连接。',
               'analysis_001：统一002指标、患者配对bootstrap、修错/误伤、候选与非候选贡献。',
               '## 执行核验',
               f'原closeout检查{len(close["checks"])}项，保存模型重放{len(replay["checks"])}项，补充检查{extra["count"]}项通过。',
               '这些是执行者核验，不替代独立审计。补充检查未重新拟合；未重新执行全部NLI配对。',
               'baseline_checks.json核对032中的U0/U2/历史SD A与031结果一致。',
               '确认bootstrap固定预测、不重训模型；多个辅助配置不是最终winner搜索。',
               '## 工程异常',
               '原GPU环境离线clone未成功，改用032专用venv只读继承research GPU库；主环境、029环境和research包未修改。',
               'NLI批量曾4→16，长窗口阶段原生进程异常退出；原因未定。保留已flush配对缓存，恢复批量4后仅续算未完成配对。',
               '日志在nli_run002.log、pipeline_resume002.log；原状态和计算覆盖记录已保留。不同batch存在浮点差异的可能，不宣称逐位等价。',
               '## 复查入口',
               '用README中的conda research DLL环境加032专用venv，运行verify032.py --output <新目录>，仅重放保存模型。',
               '默认verification_001已经存在，不覆盖；补充检查脚本及明细在engineering_001、verification_supplementary_001。']
    c.text(c.OUT / 'audit_handoff.md', '\n'.join(handoff) + '\n')
    note = '\n## 续跑核验补充\n\nNLI批量实际为4→16→4：批量16阶段进程退出，保留已算完缓存，最后恢复原批量4完成剩余配对。原因未定，未改变输入、模型或训练配方。\n\n'
    note += f'保存模型重放{len(replay["checks"])}项、补充检查{extra["count"]}项通过；详见audit_handoff.md。以上均为执行者自检，不是独立审计。\n'
    rp = c.OUT / 'report.md'
    if '## 续跑核验补充' not in rp.read_text(encoding='utf-8'):
        c.text(rp, rp.read_text(encoding='utf-8') + note)
    changed = subprocess.check_output(['git', 'diff', '--name-only'], cwd=ROOT, text=True).splitlines()
    c.put(c.OUT / 'engineering_001/tracked_changes.json', dict(paths=changed, note='No commit or push performed; 032 initially untracked.'))
    files = {}
    for base in [c.TASK, c.OUT]:
        for path in sorted(base.rglob('*')):
            if path.is_file() and '__pycache__' not in path.parts and path.name not in ['delivery_manifest.json', 'execution_status.json']:
                files[str(path.relative_to(ROOT))] = c.sha(path)
    c.put(c.OUT / 'delivery_manifest.json', dict(created_utc=c.now(), base_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(), files=files, independent_audit=False, API_calls=0))
    c.state('completed', state='completed', API_calls=0, independent_audit=False, saved_model_replay=True, supplementary_checks=extra['count'])
    print('032 continuation finalized; independent audit still pending.', flush=True)

if __name__ == '__main__':
    main()
