import csv
import hashlib
import io
import json
import os
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .biology import parse_fasta, analyze, AA
from . import store, ml

app = FastAPI(title='BioForge Lab', version='1.0.0', description='Reproducible sequence analysis and solubility regression. Research use only.')

def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())
def require(identifier, category):
    result=store.get(identifier,category)
    if result is None: raise HTTPException(404,'Record not found')
    return result

def ingest_csv(content, name, source, demo=False):
    reader=csv.DictReader(io.StringIO(content))
    if not {'id','sequence','solubility'}.issubset(reader.fieldnames or []):
        raise ValueError('CSV requires id, sequence, solubility columns; optional group column for homology clusters.')
    rows=[]; seen={}; ids=set(); duplicates=0
    for index,row in enumerate(reader,2):
        sequence=''.join((row.get('sequence') or '').split()).upper()
        analyze(sequence)
        identifier=(row.get('id') or '').strip()
        if not identifier or identifier in ids: raise ValueError(f'Row {index}: IDs must be nonempty and unique.')
        ids.add(identifier)
        try: label=float(row['solubility'])
        except (ValueError,TypeError): raise ValueError(f'Row {index}: invalid solubility.')
        if not 0<=label<=100: raise ValueError(f'Row {index}: solubility must be a percentage from 0 to 100.')
        if sequence in seen:
            if seen[sequence]!=label: raise ValueError(f'Row {index}: duplicate sequence has conflicting labels.')
            duplicates+=1; continue
        seen[sequence]=label
        rows.append({'id':identifier,'sequence':sequence,'solubility':label,'group':(row.get('group') or '').strip()})
        if len(rows)>10000: raise ValueError('Maximum 10,000 unique rows.')
    if len(rows)<12: raise ValueError('Provide at least 12 unique protein sequences.')
    groups={r['group'] or r['sequence'] for r in rows}
    if len(groups)<4: raise ValueError('Provide at least four independent groups.')
    return store.put('dataset',{'id':uid(),'name':name,'source':source,'demo':demo,'created_at':now(),'rows':rows,'count':len(rows),'duplicates_removed':duplicates,'sha256':hashlib.sha256(content.encode()).hexdigest(),'group_count':len(groups),'label_mean':sum(r['solubility'] for r in rows)/len(rows),'label_min':min(r['solubility'] for r in rows),'label_max':max(r['solubility'] for r in rows),'homology_groups':all(r['group'] for r in rows)})

@app.get('/api/health')
def health(): return {'status':'ok','version':'1.0.0'}

@app.get('/api/workspace')
def workspace():
    datasets=[{k:v for k,v in d.items() if k!='rows'} for d in store.all_records('dataset')]
    return {'datasets':datasets,'analyses':store.all_records('analysis'),'runs':store.all_records('run')}

class AnalysisRequest(BaseModel):
    name:str=Field(default='Untitled collection',min_length=1,max_length=100)
    kind:Literal['dna','protein']='protein'
    fasta:str=Field(max_length=5_000_000)

@app.post('/api/analyses')
def analysis(request:AnalysisRequest):
    try: records=parse_fasta(request.fasta,request.kind)
    except ValueError as exc: raise HTTPException(422,str(exc))
    return store.put('analysis',{'id':uid(),'name':request.name,'kind':request.kind,'created_at':now(),'records':records,'count':len(records)})

@app.post('/api/analyses/upload')
async def upload_analysis(file:UploadFile=File(...),kind:Literal['protein','dna']=Form('protein')):
    content=await file.read(5_000_001)
    if len(content)>5_000_000: raise HTTPException(413,'File exceeds 5 MB.')
    try: text=content.decode('utf-8-sig')
    except UnicodeDecodeError: raise HTTPException(422,'Upload UTF-8 FASTA text.')
    return analysis(AnalysisRequest(name=(file.filename or 'Uploaded FASTA')[:100],kind=kind,fasta=text))

@app.post('/api/datasets')
async def upload_dataset(file:UploadFile=File(...),source:str=Form(...)):
    if not source.strip() or len(source)>2000: raise HTTPException(422,'Provide a source citation, URL, and assay context (maximum 2,000 characters).')
    content=await file.read(10_000_001)
    if len(content)>10_000_000: raise HTTPException(413,'CSV exceeds 10 MB.')
    try: return ingest_csv(content.decode('utf-8-sig'),(file.filename or 'Dataset')[:100],source)
    except (ValueError,UnicodeDecodeError) as exc: raise HTTPException(422,str(exc))

@app.get('/api/datasets/{dataset_id}')
def dataset(dataset_id:str): return require(dataset_id,'dataset')

@app.get('/api/datasets/{dataset_id}/export')
def export_dataset(dataset_id:str):
    dataset=require(dataset_id,'dataset')
    output=io.StringIO();writer=csv.DictWriter(output,fieldnames=['id','sequence','solubility','group']);writer.writeheader();writer.writerows(dataset['rows'])
    return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="bioforge-dataset-{dataset_id}.csv"'})

@app.post('/api/demo')
def demo():
    existing=next((d for d in store.all_records('dataset') if d['demo']),None)
    if existing: return existing
    rng=random.Random(42)
    content=io.StringIO(); writer=csv.writer(content);writer.writerow(['id','sequence','solubility','group'])
    for i in range(160):
        seq='M'+''.join(rng.choices(AA,weights=[rng.uniform(.1,3) for _ in AA],k=rng.randint(70,360)))
        f=analyze(seq)['features']
        label=max(0,min(100,55-22*f['gravy']+rng.gauss(0,12)))
        writer.writerow([f'DEMO_{i+1:04}',seq,round(label,2),f'synthetic_{i//4:02}'])
    dataset=ingest_csv(content.getvalue(),'Solubility sandbox','Synthetic sequences and artificial labels generated with seed 42. For software demonstration only; not an experimental benchmark.',True)
    samples='\n'.join('>'+r['id']+'\n'+r['sequence'] for r in dataset['rows'][:8])
    analysis(AnalysisRequest(name='Starter protein collection',fasta=samples))
    return dataset

@app.post('/api/datasets/public/esol')
def public_esol():
    from .public_data import download_esol, REVISION
    existing=next((d for d in store.all_records('dataset') if d.get('public_import',{}).get('revision')==REVISION),None)
    if existing: return existing
    try:
        content, provenance=download_esol()
        dataset=ingest_csv(content,'eSOL · public training partition',f"eSOL experimental E. coli cell-free protein solubility. Mirror: Xiangwenqiang/eSOL, revision {REVISION}. Original archive DOI 10.18908/lsdba.nbdc00440-001. Mirror citation: Tan et al. (2025), VenusFactory, arXiv:2503.15438. Assay: chaperone-free PURE expression system. Mirror labels converted from fractions to percentages. Homology clusters unavailable; supply your own for independent evaluation.")
        dataset['public_import']=provenance
        return store.put('dataset',dataset)
    except Exception as exc:
        raise HTTPException(502,'Public import failed. Check network connectivity or import a prepared CSV. '+str(exc))

class RunRequest(BaseModel):
    dataset_id:str
    name:str=Field(default='Solubility experiment',min_length=1,max_length=100)
    model:Literal['random_forest','extra_trees']='random_forest'
    seed:int=Field(default=42,ge=0,le=2**32-1)
    trees:int=Field(default=100,ge=20,le=300)
    test_fraction:float=Field(default=.25,ge=.15,le=.4)

@app.post('/api/runs')
def run(request:RunRequest):
    dataset=require(request.dataset_id,'dataset')
    run_id=uid(); config=request.model_dump()
    try: result=ml.train(dataset,config,run_id)
    except ValueError as exc: raise HTTPException(422,str(exc))
    record={'id':run_id,'name':request.name,'dataset_id':dataset['id'],'dataset_name':dataset['name'],'dataset_provenance':{'source':dataset['source'],'public_import':dataset.get('public_import'),'duplicates_removed':dataset['duplicates_removed'],'homology_groups_supplied':dataset['homology_groups']},'demo':dataset['demo'],'created_at':now(),'config':config,**result}
    record['mlflow_status']='local artifacts only'
    if os.getenv('MLFLOW_TRACKING_URI'):
        try:
            import mlflow
            mlflow.set_tracking_uri(os.environ['MLFLOW_TRACKING_URI']);mlflow.set_experiment('BioForge Lab')
            with mlflow.start_run(run_name=request.name) as tracking:
                mlflow.log_params({**config,'dataset_sha256':dataset['sha256']})
                mlflow.log_metrics({k:v for k,v in result['metrics'].items() if v is not None})
                mlflow.log_dict(result,'evaluation.json')
                mlflow.log_artifact(str(store.DATA/'artifacts'/f'{run_id}.joblib'))
                record['mlflow_run_id']=tracking.info.run_id
                record['mlflow_status']='tracked'
        except Exception:
            record['mlflow_status']='unavailable; local record and model preserved'
    store.put('run',record)
    (store.DATA/'artifacts'/f'{run_id}.json').write_text(json.dumps(record,indent=2))
    return record

class PredictionRequest(BaseModel):
    run_id:str
    analysis_id:str

@app.post('/api/predictions')
def prediction(request:PredictionRequest):
    run=require(request.run_id,'run'); collection=require(request.analysis_id,'analysis')
    if collection['kind']!='protein': raise HTTPException(422,'Select a protein collection.')
    try: results=ml.predict(run['id'],collection['records'])
    except ValueError as exc: raise HTTPException(422,str(exc))
    training={r['sequence'] for r in require(run['dataset_id'],'dataset')['rows']}
    for result, record in zip(results,collection['records']): result['in_training_dataset']=record['sequence'] in training
    return {'run_id':run['id'],'demo':run['demo'],'results':results,'note':'Tree spread measures model disagreement, not calibrated uncertainty. Scores are research hypotheses, not measured solubility.'}

@app.get('/api/runs/{run_id}/export')
def export(run_id:str):
    record=require(run_id,'run')
    return Response(json.dumps(record,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="bioforge-{run_id}.json"'})

class AssistantRequest(BaseModel):
    run_id:str
    question:str=Field(min_length=1,max_length=1000)

@app.post('/api/assistant')
def assistant(request:AssistantRequest):
    run=require(request.run_id,'run'); d=require(run['dataset_id'],'dataset')
    m=run['metrics']; b=run['baseline']; gain=b['mae']-m['mae']
    return {'answer':f"{run['name']} held out {run['test_count']} records and trained on {run['train_count']}. Test MAE was {m['mae']:.2f} percentage points versus {b['mae']:.2f} for the mean baseline ({gain:+.2f} point improvement). The 95% bootstrap MAE interval was {run['mae_ci'][0]:.2f}–{run['mae_ci'][1]:.2f}. There were {run['group_overlap']} shared groups across the split. " + ('This is synthetic demo data: performance does not establish biological validity. ' if run['demo'] else 'Assay conditions and dataset selection limit generalization. ') + 'The next step is independent validation using held-out homology clusters and a separate assay-matched dataset. This deterministic summary uses stored run evidence; it is not an open-ended language model.', 'sources':[{'label':'Run evaluation','id':run['id']},{'label':'Dataset provenance','text':d['source']},{'label':'Split limitation','text':run['split_note']} ]}

DIST=Path(__file__).resolve().parents[2]/'frontend'/'dist'
if DIST.exists():
    app.mount('/assets',StaticFiles(directory=DIST/'assets'),name='assets')
    @app.get('/{path:path}')
    def spa(path:str):
        if path.startswith('api/'): raise HTTPException(404,'API route not found')
        return FileResponse(DIST/'index.html')
