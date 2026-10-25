"""Single entry. Status/dry-run never call an endpoint. Execution is opt-in."""
import argparse,json
import common096 as c
def main():
    p=argparse.ArgumentParser();p.add_argument('action',choices=['status','validate-runtime','preflight','choose-size','calibration','fit','main','stress','finish']);p.add_argument('--runtime');p.add_argument('--execute',action='store_true');a=p.parse_args()
    if a.action=='status':
        receipts=list((c.PRIVATE/'attempts').glob('*/*/receipt.json'))
        status='R1_INFERENCE_DONE' if (c.OUT/'R1_INFERENCE_DONE.json').exists() else 'R1_RESPONSES_PRESENT_CHECK_STAGE' if receipts else 'READY_FOR_R1' if (c.OUT/'READY_FOR_R1.json').exists() else 'OFFLINE_PREPARING'
        print(json.dumps(dict(status=status,new_HTTP_receipts=len(receipts),planned_clinical_requests=1143,runtime_configuration_present=(c.PRIVATE/'runtime.json').exists(),no_endpoint_probe=True,waiting_for_user_service_ready=status=='READY_FOR_R1'),ensure_ascii=False));return
    if not a.execute:
        print('DRY_RUN_ONLY',a.action,'No network, no calibration mutation. After user service-ready confirmation provide --runtime and --execute.');return
    if a.action=='fit':
        from calibration096 import adapt
        adapt();return
    if a.action=='finish':
        from preflight096 import done
        done();return
    if not a.runtime:p.error('--runtime is required; no environment fallback')
    import runner096 as r
    cfg=r.validate_runtime(a.runtime)
    if a.action=='validate-runtime':print('RUNTIME_LOCAL_VALIDATED — endpoint not accessed');return
    if a.action=='preflight':
        r.execute('technical',a.runtime)
        from preflight096 import inspect_and_freeze
        inspect_and_freeze()
    elif a.action=='choose-size':
        from preflight096 import forecast_and_select
        forecast_and_select(a.runtime)
    elif a.action in ['calibration','main','stress']:r.execute(a.action,a.runtime)
if __name__=='__main__':main()
