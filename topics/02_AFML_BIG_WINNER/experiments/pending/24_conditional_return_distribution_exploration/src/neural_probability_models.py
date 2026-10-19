"""Fixed-budget neural probabilities with independent parameter-only inference."""
import warnings
import numpy as np
from scipy.special import softmax
from sklearn.neural_network import MLPClassifier
from sklearn.exceptions import ConvergenceWarning

PARAMS=dict(hidden_layer_sizes=(32,16),activation='tanh',solver='adam',alpha=1.,batch_size=1024,
    learning_rate_init=.001,max_iter=60,tol=0.,n_iter_no_change=61,early_stopping=False,shuffle=True,random_state=24)


def fit_network(x,labels,weights,parameters=None):
    params=PARAMS if parameters is None else parameters
    labels=np.asarray(labels);weights=np.asarray(weights,float)
    if set(labels)!=set(range(7)) or not np.isfinite(weights).all() or (weights<=0).any():
        raise ValueError('All seven classes and positive training weights required')
    model=MLPClassifier(**params)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter('always');model.fit(x,labels,sample_weight=weights)
    for warning in caught:
        if not issubclass(warning.category,ConvergenceWarning) or 'Maximum iterations' not in str(warning.message):
            raise RuntimeError(str(warning.message))
    assert model.n_iter_==params['max_iter'] and len(model.loss_curve_)==params['max_iter']
    assert np.isfinite(model.loss_curve_).all() and model.out_activation_=='softmax'
    assert all(np.isfinite(w).all() for w in model.coefs_+model.intercepts_)
    return model,len(caught)


def forward(x,coefs,intercepts,labels):
    if len(coefs)!=3 or len(intercepts)!=3 or set(np.asarray(labels))!=set(range(7)):
        raise ValueError('Two hidden layers and seven-class softmax required')
    a=np.asarray(x,float)
    for w,b in zip(coefs[:-1],intercepts[:-1]):a=np.tanh(a@w+b)
    p=np.zeros((len(a),7));p[:,np.asarray(labels,int)]=softmax(a@coefs[-1]+intercepts[-1],axis=1)
    assert np.isfinite(p).all() and (p>=0).all();np.testing.assert_allclose(p.sum(axis=1),1,atol=1e-12)
    return p
