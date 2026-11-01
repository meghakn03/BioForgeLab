import hashlib
import json
from pathlib import Path
import numpy as np
import joblib
import platform
import Bio
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor
from sklearn.dummy import DummyRegressor
from sklearn.model_selection import GroupShuffleSplit
from sklearn.metrics import mean_absolute_error, r2_score, mean_squared_error
from .biology import analyze, FEATURE_NAMES
from .store import DATA

def vector(sequence):
    features = analyze(sequence)['features']
    return [features[name] for name in FEATURE_NAMES]

def train(dataset, config, run_id):
    rows = dataset['rows']
    x = np.array([vector(row['sequence']) for row in rows])
    y = np.array([row['solubility'] for row in rows])
    groups = [row.get('group') or hashlib.sha256(row['sequence'].encode()).hexdigest() for row in rows]
    seed = config['seed']
    splitter = GroupShuffleSplit(n_splits=1, test_size=config['test_fraction'], random_state=seed)
    tr, te = next(splitter.split(x,y,groups))
    if len(te)<3 or len(tr)<5:
        raise ValueError('Split must contain at least 5 training and 3 test records; add more groups.')
    cls = RandomForestRegressor if config['model']=='random_forest' else ExtraTreesRegressor
    model = cls(n_estimators=config['trees'], min_samples_leaf=2, random_state=seed,n_jobs=-1)
    model.fit(x[tr],y[tr])
    pred = model.predict(x[te])
    baseline = DummyRegressor(strategy='mean').fit(x[tr],y[tr]).predict(x[te])
    def metrics(p):
        return {'mae':float(mean_absolute_error(y[te],p)), 'rmse':float(np.sqrt(mean_squared_error(y[te],p))), 'r2':float(r2_score(y[te],p)) if np.var(y[te]) else None}
    rng = np.random.default_rng(seed)
    boots = [float(mean_absolute_error(y[te][idx],pred[idx])) for idx in rng.integers(0,len(te),size=(500,len(te)))]
    directory = DATA/'artifacts'
    directory.mkdir(exist_ok=True)
    joblib.dump(model,directory/f'{run_id}.joblib')
    return {'metrics':metrics(pred), 'baseline':metrics(baseline), 'mae_ci':[float(v) for v in np.quantile(boots,[.025,.975])], 'train_count':len(tr), 'test_count':len(te), 'train_ids':[rows[i]['id'] for i in tr], 'test_ids':[rows[i]['id'] for i in te], 'group_overlap':len(set(np.array(groups)[tr]) & set(np.array(groups)[te])), 'predictions':[{'name':rows[i]['id'],'observed':float(y[i]),'predicted':float(p)} for i,p in zip(te,pred)], 'importance':sorted([{'feature':k,'importance':float(v)} for k,v in zip(FEATURE_NAMES,model.feature_importances_)],key=lambda r:-r['importance']), 'versions':{'python':platform.python_version(),'biopython':Bio.__version__,'numpy':np.__version__, 'sklearn':__import__('sklearn').__version__}, 'feature_schema':FEATURE_NAMES, 'implementation_sha256':hashlib.sha256(Path(__file__).read_bytes()+(Path(__file__).parent/'biology.py').read_bytes()).hexdigest(), 'dataset_sha256':dataset['sha256'], 'uncertainty_note':'95% percentile bootstrap interval for test MAE (500 resamples). Tree spread is ensemble disagreement, not a calibrated prediction interval.', 'split_note':'Groups are held out. Exact duplicates are removed at ingestion. Supply homology cluster IDs in group for homology-aware evaluation; automatic sequence similarity clustering is not performed.'}

def predict(run_id, records):
    path = DATA/'artifacts'/f'{run_id}.joblib'
    if not path.exists():
        raise ValueError('Model artifact is missing; train a new run.')
    model = joblib.load(path)
    x = np.array([vector(row['sequence']) for row in records])
    samples = np.array([tree.predict(x) for tree in model.estimators_])
    return [{'name':r['name'], 'prediction':float(v), 'tree_std':float(s), 'tree_p10':float(lo), 'tree_p90':float(hi)} for r,v,s,lo,hi in zip(records,samples.mean(0),samples.std(0),np.quantile(samples,.1,axis=0),np.quantile(samples,.9,axis=0))]
