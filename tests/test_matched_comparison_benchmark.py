from __future__ import annotations

from hashlib import sha256
import json
import subprocess

import pytest


class FakeResponse:
    def __init__(self, code: int, body: bytes):
        self.status_code = code
        self._body = body
        self.closed = False
        self.consumed = False

    def get_data(self):
        self.consumed = True
        return self._body

    def close(self):
        self.closed = True


class FakeClient:
    def __init__(self, code=200, bodies=None):
        self.code = code
        self.bodies = iter(bodies or (b'CORPUS PRIVATE TEXT',) * 5)
        self.requests = []

    def get(self, url):
        response = FakeResponse(self.code, next(self.bodies))
        self.requests.append((url, response))
        return response


def module():
    from scripts import matched_comparison_benchmark

    return matched_comparison_benchmark


def _one_case():
    return (('enoch', '/compare?work=1En&chapter=1&verse=2', 200),)


def test_linux_current_rss_uses_kib_not_peak_or_bytes():
    assert module().parse_linux_vmrss_kib('Name:\tpython\nVmPeak:\t900000 kB\nVmRSS:\t123456 kB\n') == 123456
    with pytest.raises(ValueError, match='VmRSS'):
        module().parse_linux_vmrss_kib('VmPeak:\t900000 kB\n')


def test_worker_separates_first_and_warm_request_and_hashes_body_without_exposing_it():
    client = FakeClient()
    ticks = iter((0, 7_000_000, 7_500_000, 9_000_000, 10_000_000, 11_000_000))
    result = module().measure_routes(
        client, _one_case(), repeat_count=2, clock_ns=lambda: next(ticks),
    )
    assert result[0]['first_ms'] == 7.0
    assert result[0]['warm_ms'] == [1.5, 1.0]
    assert result[0]['warm_median_ms'] == 1.25
    assert result[0]['expected_status'] == 200
    assert result[0]['body_sha256'] == sha256(b'CORPUS PRIVATE TEXT').hexdigest()
    assert all(resp.consumed and resp.closed for _, resp in client.requests)
    assert 'CORPUS PRIVATE TEXT' not in json.dumps(result)


def test_worker_accepts_and_hashes_explicit_fail_closed_400():
    client = FakeClient(code=400)
    ticks = iter((0, 1_000_000, 2_000_000, 3_000_000))
    result = module().measure_routes(
        client, (('ambiguous', '/compare?work=PssSol&chapter=1&verse=5', 400),),
        repeat_count=1, clock_ns=lambda: next(ticks),
    )
    assert result[0]['expected_status'] == 400
    assert result[0]['first_ms'] == result[0]['warm_ms'][0] == 1.0


def test_worker_refuses_status_mismatch_and_response_hash_drift():
    m = module()
    bad = FakeClient(code=500)
    with pytest.raises(AssertionError, match='HTTP 200.*500'):
        m.measure_routes(bad, _one_case(), repeat_count=1, clock_ns=iter((0, 10)).__next__)
    assert bad.requests[0][1].closed
    changed = FakeClient(bodies=(b'source one', b'source TWO'))
    with pytest.raises(AssertionError, match='HTML digest drift'):
        m.measure_routes(changed, _one_case(), repeat_count=1, clock_ns=iter((0, 10, 10, 20)).__next__)
    assert all(item.closed for _, item in changed.requests)


def test_runner_handles_nonzero_exit_timeout_and_missing_json_fail_closed():
    m = module()
    def failed(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 2, 'UNSAFE BODY', 'fatal error')
    with pytest.raises(RuntimeError, match='exited 2'):
        m.run_child(['python', 'script'], runner=failed)
    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs['timeout'])
    with pytest.raises(RuntimeError, match='timed out'):
        m.run_child(['python', 'script'], runner=timed_out)
    def missing(*args, **kwargs):
        return subprocess.CompletedProcess(args[0], 0, 'no output', '')
    with pytest.raises(ValueError, match='MATCHED_CHILD_JSON'):
        m.run_child(['python', 'script'], runner=missing)


def _record(variant, commit, digest='abc', version='13.1.0', status=200):
    return {
        'variant': variant, 'commit': commit,
        'source_commit': 'ocp-pin', 'tf_data_version': '1.0',
        'python': '3.12.15', 'text_fabric': version,
        'cases': [{'label': 'enoch', 'expected_status': status,
                   'body_sha256': digest, 'first_ms': 2.0,
                   'warm_ms': [1.0, 1.3], 'warm_median_ms': 1.15}],
        'app_setup_s': 1.2,
        'memory': {'unit': 'KiB', 'rss_before_app_kib': 100,
                   'rss_after_app_kib': 200, 'rss_after_requests_kib': 220,
                   'peak_rss_kib': 240},
    }


def test_matched_results_reject_any_version_provenance_status_or_html_drift():
    m = module()
    baseline = _record('baseline', 'base')
    candidate = _record('candidate', 'new')
    assert m.validate_pair(baseline, candidate, baseline_sha='base', candidate_sha='new',
                           source_commit='ocp-pin')['enoch']['baseline_warm_median_ms'] == 1.15
    for changed in [
        {**candidate, 'commit': 'wrong'},
        {**candidate, 'source_commit': 'other'},
        {**candidate, 'text_fabric': '14.0.0'},
        {**candidate, 'tf_data_version': 'other'},
        {**candidate, 'cases': [{**candidate['cases'][0], 'body_sha256': 'tampered'}]},
        {**candidate, 'cases': [{**candidate['cases'][0], 'expected_status': 500}]},
        {**candidate, 'memory': {**candidate['memory'], 'unit': 'bytes'}},
    ]:
        with pytest.raises((ValueError, AssertionError)):
            m.validate_pair(baseline, changed, baseline_sha='base', candidate_sha='new',
                            source_commit='ocp-pin')


def test_corpus_report_rejects_wrong_commit_and_failed_semantic_parity(tmp_path):
    m = module()
    report = tmp_path / 'conversion-report.json'
    report.write_text(json.dumps({'status': 'ok', 'provenance': {'upstream_commit': 'source'},
                                  'semantic_checks': {'version': True}}))
    assert m.verify_corpus_report(tmp_path, 'source') is None
    with pytest.raises(ValueError, match='source commit'):
        m.verify_corpus_report(tmp_path, 'wrong')
    report.write_text(json.dumps({'status': 'ok', 'provenance': {'upstream_commit': 'source'},
                                  'semantic_checks': {'version': False}}))
    with pytest.raises(ValueError, match='semantic'):
        m.verify_corpus_report(tmp_path, 'source')


def test_abba_schedule_has_isolated_four_runs_not_concurrent_reuse():
    assert module().ABBA_SCHEDULE == ('baseline', 'candidate', 'candidate', 'baseline')

