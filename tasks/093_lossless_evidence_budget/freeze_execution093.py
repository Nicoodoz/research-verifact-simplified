import common093 as c
def main():
    names=['api093.py','test093.py','common093.py','operation093.py','prepare093.py','build_pool093.py']
    c.put(c.OUT/'execution_freeze.json',dict(utc=c.now(),source_sha256={str((c.TASK/n).relative_to(c.ROOT)).replace('\\','/'):c.sha(c.TASK/n) for n in names},API_cap_cny=20,tests='test093.py must pass before paid preflight',no_result_dependent_variant=True))
    print('Execution frozen.')
if __name__=='__main__':main()
