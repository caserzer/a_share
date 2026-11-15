import numpy as np
from sklearn.linear_model import Ridge,LogisticRegression

def test_penalty_identity_and_nonidentical_columns():
    b1,b2=2.,-1.;s=b1+b2
    assert b1*b1+b2*b2==s*s/2+(b1-b2)**2/2
    # Equality of inputs is essential; merging differing columns is not equivalent.
    x1,x2=3.,4.
    assert x1*b1+x2*b2!=x1*s

def test_synthetic_equivalent_regularized_fit():
    rng=np.random.default_rng(35104);x=rng.normal(size=(240,3));y=2*x[:,0]-.7*x[:,1]+.1*rng.normal(size=240)
    duplicate=np.column_stack([x,x[:,0]]);compressed=x.copy();compressed[:,0]*=np.sqrt(2)
    a=Ridge(alpha=10).fit(duplicate,y);b=Ridge(alpha=10).fit(compressed,y)
    np.testing.assert_allclose(a.predict(duplicate),b.predict(compressed),atol=1e-12)
    # Dropping the duplicate without its scale changes the objective.
    naive=Ridge(alpha=10).fit(x,y)
    assert np.max(abs(a.predict(duplicate)-naive.predict(x)))>1e-3
    binary=(y>np.median(y)).astype(int)
    a=LogisticRegression(C=1,tol=1e-10,max_iter=2000).fit(duplicate,binary)
    b=LogisticRegression(C=1,tol=1e-10,max_iter=2000).fit(compressed,binary)
    np.testing.assert_allclose(a.predict_proba(duplicate),b.predict_proba(compressed),atol=1e-7)
