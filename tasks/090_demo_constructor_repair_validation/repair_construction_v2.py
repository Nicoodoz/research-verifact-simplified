"""Last source-compatibility repair: do not trust LLM alternative grouping across facts/times."""
from construct090 import *
def split_alternatives(src,obj):
    obj=copy.deepcopy(obj);units={u['id']:u for u in src['units']};groups=[];audit=[]
    for i,g in enumerate(obj['groups']):
        buckets={}
        for cite in g['alternatives']:
            c=citation(cite,src);assert c['valid'];u=units[c['unit_id']];m=u.get('metadata') or {}
            key=(norm(c['original']),m.get('date'),m.get('time'),m.get('note_id'))
            buckets.setdefault(key,[]).append(cite)
        for v in buckets.values():groups.append({**g,'alternatives':v})
        audit.append(dict(original_group=i,before_alternatives=len(g['alternatives']),separate_constraints=len(buckets),unit_ids=[unit_id(c) for c in g['alternatives']]))
    obj['groups']=groups;return obj,audit
def main():
    final=OUT/'final';final.mkdir(parents=True,exist_ok=True)
    freeze=final/'source_repair_freeze.json'
    if not freeze.exists():put(freeze,dict(created_utc=now(),engineering_round=2,reason='Distinct attributes/times were incorrectly exchangeable in actual P groups; conservative source-only separation, no target outcomes',
        sources={p.relative_to(ROOT).as_posix():sha(p) for p in (TASK/'repair_construction_v2.py',OUT/'constructor_freeze.json',OUT/'demonstration_freeze.json',OUT/'construction_summary.json')}))
    for rel,d in read(freeze)['sources'].items():assert sha(ROOT/rel)==d
    original=lines(ROOT/'outputs/071_judge_icl_feasibility/examples.jsonl');srcs=read(OUT/'source_units.json');old=read(OUT/'construction_summary.json')
    arms=read(OUT/'demonstrations.json');records=[];audits=[]
    for i,(ex,r) in enumerate(zip(original,old)):
        src=srcs[ex['proposition_id']];v=r['P90'];p=final/'construction'/f'slot{i+1}_P90.json'
        if p.exists():updated=read(p)
        elif v.get('constructor_output') and v['usable']:
            obj,audit=split_alternatives(src,v['constructor_output']);sel=select_p(ex,src,obj,round(token_proxy(ex['reference'])*.5));assert sel['usable']
            updated={**v,**sel,'initial_selected_ids':sel['selected_ids'][:],'added_ids':[],
                'constructor_resampled':False,'original_constructor_receipt':v['constructor_receipt'],'alternative_split_audit':audit,'engineering_round':2}
            if sel['selected_ids']!=v['initial_selected_ids'] and set(sel['selected_ids'])!=set(all_ids(src)):
                j=api.freeze_job('review_v2','P90',ex['proposition_id'],ex['sid'],body(CHECK,check_payload(ex,src,sel['selected_ids']),MODEL))
                checked,rp,err=get_json(j);review=repair(ex,src,sel['selected_ids'],checked)
                updated.update(review=review,review_output=checked,review_receipt=rp,review_parse_error=err,added_ids=review.get('added_ids',[]),selected_ids=review['selected_ids'],usable=review['review_valid'])
                if not review['review_valid']:updated.update(status='review_v2_unusable',selected_ids=all_ids(src))
            elif sel['selected_ids']==v['initial_selected_ids']:
                updated.update(selected_ids=v['selected_ids'],added_ids=v.get('added_ids',[]),review_reused_unchanged_input=True)
            put(p,updated)
        else:updated=v;put(p,updated)
        updated.update(chars=len(render_reference(src,updated['selected_ids'])),proxy_tokens=token_proxy(render_reference(src,updated['selected_ids'])))
        r={**r,'P90':updated};records.append(r);arms['P90'][i]['reference']=render_reference(src,updated['selected_ids'])
        source_check(ex['reference'],src,updated['selected_ids'],arms['P90'][i]['reference'])
        audits.append(dict(slot=i+1,id=r['id'],old_P_ids=v['selected_ids'],final_P_ids=updated['selected_ids'],split=updated.get('alternative_split_audit',[])))
    oldt=read(ROOT/'outputs/087_f4_evidence_intervention/templates.json');systems={'B':oldt['systems']['B'],**{a:render_system(oldt['systems']['B'],oldt['header'],arms[a]) for a in arms}}
    usable={a:all(r[a]['usable'] for r in records) for a in ('P90','Q90')};active=['B','F4']+[a for a in ('P90','Q90') if usable[a]]
    put(final/'demonstrations.json',arms);put(final/'construction_summary.json',records)
    put(final/'templates.json',dict(systems=systems,active_arms=active,usable=usable,hashes={a:h(s) for a,s in systems.items()},chars={a:len(s) for a,s in systems.items()}))
    put(PUB/'source_repair_v2.json',dict(engineering_round=2,constructor_new_calls=0,reason='source/time compatibility correction, not downstream optimization',cases=audits,
        differences='v1 groups allowed model-declared alternatives; v2 separates different normalized quotes or note/date/time. Both v1 and original calls remain intact.'))
    pubrec=[dict(ordinal=r['ordinal'],id=r['id'],original_chars=r['original_chars'],original_proxy_tokens=r['original_proxy_tokens'],
        **{a:{k:r[a].get(k) for k in ('usable','status','initial_selected_ids','selected_ids','added_ids','chars','proxy_tokens')} for a in ('P90','Q90')}) for r in records]
    put(PUB/'final_construction_summary.json',pubrec)
    distinct=[a for a in ('P90','Q90') if usable[a] and systems[a]!=systems['F4']]
    branch='four_arm' if len(distinct)==2 and systems['P90']!=systems['Q90'] else 'shared_compression' if len(distinct)==2 else 'one_candidate' if distinct else 'B_F4_coverage'
    put(PUB/'final_branch.json',dict(branch=branch,engineering_round=2,active_arms=active,distinct_compressed=distinct,usable=usable,system_hashes={a:h(s) for a,s in systems.items()},
        no_target_results_seen=True,P_primary_testable='P90' in distinct,P_Q_distinct_inputs=len(distinct)==2 and systems['P90']!=systems['Q90'],
        equal_length_control=False,interpretation='Earlier branch field special_mechanism_identifiable meant distinct inputs only; unequal lengths do not isolate pure mechanism.'))
    put(final/'demonstration_freeze.json',dict(created_utc=now(),files={p.relative_to(final).as_posix():sha(p) for p in final.rglob('*') if p.is_file()},
        inherited_first_round_freeze_sha256=sha(OUT/'demonstration_freeze.json')))
    print(canonical(dict(branch=branch,chars={a:len(s) for a,s in systems.items()},P_ids=[r['P90']['selected_ids'] for r in records],cost=sum(x['cost_or_unknown_cny'] for x in api.state()[0]))))
if __name__=='__main__':main()
