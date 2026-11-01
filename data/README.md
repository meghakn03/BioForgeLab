# Data policy

Local database and model artifacts are generated here and excluded from Git.

The in-app sandbox is entirely synthetic: 160 artificial canonical sequences and labels from a fixed seeded recipe. Never report its performance as experimental evidence.

To use measured protein solubility, import a UTF-8 CSV with `id,sequence,solubility,group`. Labels are percentages, not 0–1 fractions. The optional `group` field should be computed externally using a homology clustering tool such as MMseqs2; choose and document identity and coverage thresholds for the research question. Exact duplicate sequences are removed and conflicting labels rejected. Missing groups fall back to exact sequence hashes and do not prevent homolog leakage.

Public source: [eSOL archive](https://dbarchive.biosciencedbc.jp/en/esol/data-1.html), DOI 10.18908/lsdba.nbdc00440-001. Its cell-free expression context must accompany any interpretation. Do not substitute small-molecule ESOL datasets: they describe a different task. Check original source terms before redistributing data.
