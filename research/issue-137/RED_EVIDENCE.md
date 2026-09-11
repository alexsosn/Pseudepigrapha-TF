# RED gate evidence

The RED contract was committed before implementation at `6e4f49d9ca6d8a0e969e5f70a69906ca763209cf`.

`tests/test_ci_full_corpus_contract.py::test_pinned_full_corpus_job_verifies_serialized_historical_classification_api` requires the pinned full-corpus CI path to exercise a historical-classification acceptance check. On the pre-implementation workflow inherited from `main`, there is no such invocation, so that assertion is intentionally RED.

The subsequent acceptance-script commit does not change the workflow contract; until the existing pinned acceptance path is wired to call it, the RED assertion remains unsatisfied.