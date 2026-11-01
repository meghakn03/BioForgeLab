# Protein solubility: an honest baseline

## Question
Can sequence-derived physicochemical descriptors predict assay-specific protein solubility better than predicting the training-set mean?

## Implemented protocol
Import measured percentage labels, canonical sequences, and externally computed homology clusters. Validate the alphabet and label range; reject conflicting duplicate labels; remove identical duplicates. Preserve the raw CSV fingerprint and source/assay declaration. Split groups once using GroupShuffleSplit, keeping held-out labels out of model fitting. Evaluate a random forest or extra-trees regressor against the training mean using MAE, RMSE, and R². Save configurations, library versions, row IDs, dataset fingerprint, model, test predictions, and bootstrap interval.

Features are length, molecular weight, theoretical pI, GRAVY, aromaticity, instability index, secondary-structure propensity fractions, and amino acid fractions, computed with Biopython. These are sequence descriptors, not structure predictions.

## Demonstration and interpretation
The bundled data are synthetic. Their labels deliberately depend on GRAVY plus seeded noise, so feature importance and performance show that the software functions. They cannot support a claim that the model predicts measured protein solubility. Actual metrics are computed live, never hard-coded into the dashboard.

## Verified public-data run

The pinned Xiangwenqiang/eSOL training partition (revision `0a80a64ab83fdd3b4ac6b4d68c8bb97fa6d4c1e0`) contains 2,481 canonical proteins. BioForge imports only that partition, verifies SHA-256 `033320b349897ad11f0d6820dcb8b999f163e4f1f991825d54046eadf9f9178f`, and converts fractional labels to percentages. A 100-tree random forest with seed 42 and 25% exact-sequence group hold-out trained on 1,860 proteins and tested on 621: MAE **20.33 pp**, mean-baseline MAE **29.70 pp**, RMSE **24.82 pp**, R² **0.436**, and test-record bootstrap MAE interval **19.32–21.38 pp**. These are a verified software baseline on the mirrored training partition, not an independent homology-controlled benchmark. The mirror provides no homology cluster IDs; related sequences may span the split. The upstream validation/test files remain unused.

Sources: [pinned mirror](https://huggingface.co/datasets/Xiangwenqiang/eSOL/tree/0a80a64ab83fdd3b4ac6b4d68c8bb97fa6d4c1e0), [original eSOL assay archive](https://dbarchive.biosciencedbc.jp/en/esol/data-1.html).

## Limitations
Group splitting prevents overlap only for the supplied group definition. Without external homology clustering it prevents exact duplication alone. The fixed test split is not a tuning set; reserve independent validation before selecting a final model. The percentile bootstrap of test-record MAE assumes independent records and can understate uncertainty for correlated sequences; a group bootstrap is needed for scientific inference on clustered datasets. Tree spread is not calibrated uncertainty. Impurity feature importance can be biased and is not mechanistic evidence. Predictions depend on the assay, organism, expression system, tags, and preprocessing; this version does not encode assay covariates. No clinical claims or universal protein property predictions follow from these scores.

## Next scientific milestone
Establish explicit homology clusters with recorded tool version, compare both baselines on an untouched assay-matched external set, and report dataset selection and failure modes. Protein language model embeddings can be added only after this controlled baseline.
