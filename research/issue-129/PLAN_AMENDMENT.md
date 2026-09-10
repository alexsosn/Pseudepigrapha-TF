# Issue #129 plan amendment after RED

## Observed RED

Strict pytest warning mode at `1a3aa3bb71ed54150d6459cf32992a41f9fe072d` produced `1 failed, 558 passed` in run `34484328515`.

The failure was not one of the two previously visible cleanup warnings. Instead it exposed an unowned resource leak in `tests/test_comparison_web.py::test_stock_tf_browser_and_compare_route_coexist_on_one_flask_app`:

- `client.get('/data/static/comparison.css').get_data(...)` materializes a Flask/Werkzeug file-backed response;
- the test discards the response object without calling `close()`;
- under `filterwarnings = ["error"]`, Python reports the resulting unclosed `comparison.css` file handle as a `PytestUnraisableExceptionWarning` / `ResourceWarning`.

This is test-resource ownership, not a production static-serving defect. The production route is stock Text-Fabric/Flask and file-backed responses are expected to be closed by the WSGI server/client lifecycle; the test must close the response it owns.

## Cleanup-warning behavior under strict filters

Inspection of `writer._warn_nonfatal()` shows that it deliberately catches `BaseException` around `warnings.warn(...)`. That is required so an error-configured warning filter or custom warning hook cannot replace an already-established transaction outcome.

Therefore the original two cleanup diagnostics will not themselves fail under repository-wide `filterwarnings = ["error"]`: the error filter raises the warning as an exception and `_warn_nonfatal()` intentionally swallows it. To keep those diagnostics tested, their owning tests must explicitly install `pytest.warns(...)`, which captures the warnings without turning them into transaction-changing exceptions.

## Amended GREEN plan

1. Keep global `filterwarnings = ["error"]` unchanged.
2. In the comparison-web test, retain the CSS response object and close it in `finally` after `get_data()`.
3. In the two cleanup-interruption tests, wrap the exact installation call in `pytest.warns(RuntimeWarning, match=...)` with distinct rollback-restored vs committed-install message fragments.
4. Preserve all original exception identity, result, and filesystem assertions.
5. Change no production code.
6. Re-run CI. If strict warning mode exposes further unexpected Python warnings, stop and investigate each one rather than adding ignores.
7. Final independent review must verify that the CSS fix closes the owned response rather than suppressing `ResourceWarning`, and that `pytest.warns` does not alter the transaction semantics being tested.
