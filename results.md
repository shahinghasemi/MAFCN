| description | emb | feature_list | folds | threshold | batch-auto | batch-model | epoch-auto | epoch-model | dropout | accuracy | auc | f1 |
|-------------|-----|--------------|-------|-----------|------------|-------------|------------|-------------|---------|----------|-----|----|
| without batch-normalization | 32 | ["structure", "target", "enzyme", "pathway"] | 5 | 0.5 | 1000 | 1000 | 10 | 10 | 0.4 | 12% | 51% | - |
| - | 32 | ["structure", "target", "enzyme", "pathway"] | 5 | 0.3 | 64 | 64 | 1000 | 1000 | 0.4 | 11% | 47% ||