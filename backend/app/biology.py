"""Validated canonical sequence analysis. No inferred clinical interpretation."""
from collections import Counter
from io import StringIO
import hashlib
from Bio import SeqIO
from Bio.Seq import Seq
from Bio.SeqUtils import gc_fraction
from Bio.SeqUtils.ProtParam import ProteinAnalysis

AA = 'ACDEFGHIKLMNPQRSTVWY'
FEATURE_NAMES = ['length', 'molecular_weight', 'isoelectric_point', 'gravy', 'aromaticity', 'instability_index', 'helix', 'turn', 'sheet'] + list(AA)

def analyze(sequence, kind='protein'):
    sequence = ''.join(sequence.split()).upper()
    alphabet = set(AA if kind == 'protein' else 'ACGT')
    invalid = sorted(set(sequence) - alphabet)
    if not sequence or invalid:
        raise ValueError('Empty sequence or unsupported residues: ' + ', '.join(invalid))
    if len(sequence) > 50000:
        raise ValueError('Maximum sequence length is 50,000 residues.')
    base = {'sequence': sequence, 'length': len(sequence), 'kind': kind, 'sha256': hashlib.sha256(sequence.encode()).hexdigest()}
    counts = Counter(sequence)
    base['composition'] = {x: round(counts[x] / len(sequence) * 100, 3) for x in sorted(alphabet)}
    if kind == 'dna':
        codons = Counter(sequence[i:i+3] for i in range(0, len(sequence)-2, 3))
        base.update(gc_content=round(gc_fraction(sequence)*100, 3), codon_usage=dict(sorted(codons.items())), translation=str(Seq(sequence[:len(sequence)//3*3]).translate()), trailing_bases=len(sequence)%3, features_note='Codons and translation use forward frame +1; no ORF inference.')
    else:
        p = ProteinAnalysis(sequence)
        h,t,s = p.secondary_structure_fraction()
        values = [len(sequence),p.molecular_weight(),p.isoelectric_point(),p.gravy(),p.aromaticity(),p.instability_index(),h,t,s] + [counts[x]/len(sequence) for x in AA]
        base['features'] = dict(zip(FEATURE_NAMES, [round(float(v), 5) for v in values]))
    return base

def parse_fasta(text, kind):
    if kind not in ('dna','protein'):
        raise ValueError('Sequence type must be dna or protein.')
    if not text.strip().startswith('>'):
        raise ValueError('FASTA must begin with a > identifier.')
    records = []
    ids = set()
    for record in SeqIO.parse(StringIO(text), 'fasta'):
        if record.id in ids:
            raise ValueError('Duplicate FASTA identifier: '+record.id)
        ids.add(record.id)
        try:
            result = analyze(str(record.seq), kind)
        except ValueError as exc:
            raise ValueError(f'{record.id}: {exc}') from exc
        result.update(name=record.id, description=record.description)
        records.append(result)
        if len(records)>2000:
            raise ValueError('Maximum 2,000 records per upload.')
    if not records:
        raise ValueError('No sequences found.')
    return records
