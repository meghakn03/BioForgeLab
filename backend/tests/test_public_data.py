import hashlib
from unittest.mock import patch
import pytest
from backend.app import public_data

class Download:
    def __init__(self, content): self.content=content
    def __enter__(self): return self
    def __exit__(self,*args): pass
    def read(self,limit): return self.content[:limit]

def test_public_adapter_units_and_exclusions():
    raw=b'name,aa_seq,gene,label\np1,MKTA,g1,0.65\np2,MXX,g2,0.2\n'
    with patch.object(public_data,'EXPECTED_SHA256',hashlib.sha256(raw).hexdigest()),patch.object(public_data.urllib.request,'urlopen',return_value=Download(raw)):
        csv, meta=public_data.download_esol()
    assert 'p1,MKTA,65.0,' in csv
    assert meta['excluded_ids']==['p2']
    assert 'train only' in meta['source_partition']

def test_public_adapter_rejects_modified_download():
    with patch.object(public_data.urllib.request,'urlopen',return_value=Download(b'modified')):
        with pytest.raises(ValueError,match='checksum mismatch'):
            public_data.download_esol()
