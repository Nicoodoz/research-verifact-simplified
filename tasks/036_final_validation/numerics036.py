"""Import035 numerical helpers without colliding with retrieval's generic common.py."""
import importlib.util,sys
import common036 as c
def load(alias,path):
    spec=importlib.util.spec_from_file_location(alias,path);module=importlib.util.module_from_spec(spec);sys.modules[alias]=module;spec.loader.exec_module(module);return module
folder=c.ROOT/'tasks/035_lambda_boundary_calibration'
old=load('_036_common035',folder/'common.py')
previous=sys.modules.get('common');sys.modules['common']=old
try:
    l=load('_036_learning035',folder/'learning.py');a=load('_036_analysis035',folder/'analysis.py')
finally:
    if previous is None:sys.modules.pop('common',None)
    else:sys.modules['common']=previous
sys.path.insert(0,str(c.ROOT/'tasks/022_competition_aware_support_calibration'))
import calibration022 as cal
