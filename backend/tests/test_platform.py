import os
import tempfile
os.environ['BIOFORGE_DATA_DIR']=tempfile.mkdtemp(prefix='bioforge-tests-')
os.environ.pop('DATABASE_URL',None)
os.environ.pop('MLFLOW_TRACKING_URI',None)
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.biology import analyze, parse_fasta
import pytest
client=TestClient(app)

def test_biology_and_validation():
    dna=analyze('ATGGCCTAA','dna')
    assert dna['gc_content']==pytest.approx(44.444,abs=.001)
    assert dna['translation']=='MA*'
    assert dna['codon_usage']=={'ATG':1,'GCC':1,'TAA':1}
    assert sum(analyze('ACDEFGHIKLMNPQRSTVWY')['composition'].values())==100
    with pytest.raises(ValueError): parse_fasta('>a\nMXX','protein')
    with pytest.raises(ValueError): parse_fasta('>a\nMA\n>a\nMC','protein')
    assert client.post('/api/analyses',json={'fasta':'>empty','kind':'dna'}).status_code==422

def test_complete_reproducible_workflow():
    dataset=client.post('/api/demo').json()
    assert dataset['demo'] and dataset['count']==160
    config={'dataset_id':dataset['id'],'name':'Test run','seed':42,'trees':20}
    first=client.post('/api/runs',json=config)
    assert first.status_code==200,first.text
    run=first.json()
    assert run['group_overlap']==0
    assert not set(run['train_ids'])&set(run['test_ids'])
    again=client.post('/api/runs',json=config).json()
    assert run['metrics']==pytest.approx(again['metrics'],abs=1e-12)
    assert run['test_ids']==again['test_ids']
    assert run['mae_ci'][0]<=run['metrics']['mae']<=run['mae_ci'][1]
    collection=client.post('/api/analyses',json={'name':'Novel candidates','kind':'protein','fasta':'>candidate\nMKTAYIAKQRQISFVKSHFSRQDILDLWIYHTQGYFP'}).json()
    prediction=client.post('/api/predictions',json={'run_id':run['id'],'analysis_id':collection['id']}).json()
    assert 0<=prediction['results'][0]['prediction']<=100
    assert prediction['results'][0]['in_training_dataset'] is False
    assert client.get('/api/runs/'+run['id']+'/export').json()['dataset_sha256']==dataset['sha256']
    summary=client.post('/api/assistant',json={'run_id':run['id'],'question':'Explain'}).json()
    assert 'synthetic' in summary['answer'].lower()
    assert len(summary['sources'])==3

def test_bad_dataset_and_missing_records():
    response=client.post('/api/datasets',files={'file':('bad.csv','id,sequence,solubility\nx,MKTA,101','text/csv')},data={'source':'Test assay'})
    assert response.status_code==422
    assert client.post('/api/runs',json={'dataset_id':'missing'}).status_code==404
    assert client.post('/api/analyses',json={'fasta':'MKTA'}).status_code==422

def test_conflicting_duplicate_labels():
    csv='id,sequence,solubility\na,MKTA,25\nb,MKTA,70'
    response=client.post('/api/datasets',files={'file':('conflict.csv',csv)},data={'source':'Test'})
    assert response.status_code==422 and 'conflicting' in response.text
