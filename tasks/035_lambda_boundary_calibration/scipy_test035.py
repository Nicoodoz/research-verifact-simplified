import numpy as np
from scipy.optimize import minimize
def f(x):
    return float(((x-np.array([1.,2.]))**2).sum()), 2*(x-np.array([1.,2.]))
print("before", flush=True)
r=minimize(f,[0.,0.],jac=True,method="L-BFGS-B",bounds=[(-5,5),(-5,5)])
print("after",r.success,r.x,r.fun,flush=True)
