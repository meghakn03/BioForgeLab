"""Pinned public data adapter. Does not silently merge the source test split."""
import csv
import io
import hashlib
import urllib.request
from .biology import analyze
REVISION='0a80a64ab83fdd3b4ac6b4d68c8bb97fa6d4c1e0'
URL=f'https://huggingface.co/datasets/Xiangwenqiang/eSOL/resolve/{REVISION}/train.csv'
EXPECTED_SHA256='033320b349897ad11f0d6820dcb8b999f163e4f1f991825d54046eadf9f9178f'

def download_esol():
    request=urllib.request.Request(URL,headers={'User-Agent':'BioForge-Lab/1.0'})
    with urllib.request.urlopen(request,timeout=45) as response:
        raw=response.read(2_000_001)
    if len(raw)>2_000_000: raise ValueError('Public dataset unexpectedly exceeds size limit.')
    digest=hashlib.sha256(raw).hexdigest()
    if digest!=EXPECTED_SHA256: raise ValueError('Public dataset checksum mismatch. Import stopped.')
    reader=csv.DictReader(io.StringIO(raw.decode('utf-8-sig')))
    if not {'name','aa_seq','label'}.issubset(reader.fieldnames or []): raise ValueError('Unexpected public dataset schema.')
    output=io.StringIO(); writer=csv.writer(output);writer.writerow(['id','sequence','solubility','group'])
    skipped=[]
    for row in reader:
        try:
            sequence=row['aa_seq'].strip().upper()
            analyze(sequence)
            fraction=float(row['label'])
            if not 0<=fraction<=1: raise ValueError('Expected solubility fraction between 0 and 1.')
        except ValueError:
            skipped.append(row['name']);continue
        writer.writerow([row['name'],sequence,round(fraction*100,8),''])
    return output.getvalue(),{'revision':REVISION,'raw_sha256':digest,'source_url':URL,'source_partition':'train only; upstream valid and test partitions are not imported','excluded_ids':skipped,'label_transform':'Upstream 0–1 fractions multiplied by 100 to percentage points.','licence_declaration':'Apache-2.0 in mirror dataset card; consult original source terms.','homology_warning':'No homology clusters supplied by this mirror. Exact-sequence grouping only; not homology-independent validation.'}
