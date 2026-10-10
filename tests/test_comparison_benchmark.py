from __future__ import annotations

import json

import pytest


class FakeResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.body = body
        self.consumed = False
        self.closed = False

    def get_data(self):
        self.consumed = True
        return self.body

    def close(self):
        self.closed = True


class FakeClient:
    def __init__(self, status_code=200):
        self.status_code = status_code
        self.responses = []
        self.urls = []

    def get(self, url):
        self.urls.append(url)
        response = FakeResponse(self.status_code, b"SENSITIVE-CORPUS-TEXT")
        self.responses.append(response)
        return response


def benchmark(*args, **kwargs):
    # Import inside each test so that an unimplemented module produces focused
    # RED cases without aborting unrelated pytest collection.
    from pseudepigrapha_tf.benchmark import benchmark_comparison_client

    return benchmark_comparison_client(*args, **kwargs)


def test_benchmark_separates_setup_and_first_request_from_repeated_warm_requests():
    client = FakeClient()
    ticks = iter((0, 1_500_000, 2_000_000, 2_500_000, 3_000_000, 3_500_000))

    result = benchmark(
        client,
        (("ordinary", "/compare?work=Demo&chapter=1&verse=1", 200),),
        repetitions=2,
        clock_ns=lambda: next(ticks),
        setup_seconds=3.25,
        source_commit="pinned123",
    )

    assert result["setup_seconds"] == 3.25
    assert result["source_commit"] == "pinned123"
    assert len(result["cases"]) == 1
    case = result["cases"][0]
    assert case["label"] == "ordinary"
    assert case["expected_status"] == 200
    assert case["first_request_ms"] == 1.5
    assert case["warm_request_ms"] == [0.5, 0.5]
    assert case["warm_median_ms"] == 0.5
    assert case["warm_min_ms"] == 0.5
    assert case["warm_max_ms"] == 0.5
    assert client.urls == ["/compare?work=Demo&chapter=1&verse=1"] * 3
    assert all(item.consumed and item.closed for item in client.responses)
    assert "SENSITIVE-CORPUS-TEXT" not in json.dumps(result)


def test_benchmark_accepts_deliberate_fail_closed_http_400_and_records_exact_status():
    client = FakeClient(status_code=400)
    ticks = iter((0, 10_000_000, 10_000_000, 20_000_000))
    result = benchmark(
        client,
        (("ambiguous", "/compare?work=PssSol&chapter=1&verse=5", 400),),
        repetitions=1,
        clock_ns=lambda: next(ticks),
        setup_seconds=0.0,
        source_commit="pinned123",
    )
    case = result["cases"][0]
    assert case["expected_status"] == 400
    assert case["first_request_ms"] == 10.0
    assert case["warm_request_ms"] == [10.0]
    assert all(item.closed for item in client.responses)


def test_benchmark_fails_on_unexpected_status_but_still_consumes_and_closes_response():
    client = FakeClient(status_code=500)
    ticks = iter((0, 1_000_000))
    with pytest.raises(AssertionError, match="ordinary.*expected HTTP 200.*got 500"):
        benchmark(
            client,
            (("ordinary", "/compare?work=Demo&chapter=1&verse=1", 200),),
            repetitions=1,
            clock_ns=lambda: next(ticks),
            setup_seconds=0.1,
            source_commit="pinned123",
        )
    assert len(client.responses) == 1
    assert client.responses[0].consumed and client.responses[0].closed


@pytest.mark.parametrize(
    "cases,repetitions",
    [
        ((("valid", "/compare?work=A&chapter=1&verse=1", 200),), 0),
        ((("valid", "/compare?work=A&chapter=1&verse=1", 200),), -1),
        ((("duplicate", "/compare?work=A&chapter=1&verse=1", 200),
          ("duplicate", "/compare?work=B&chapter=1&verse=1", 200)), 2),
        ((("invalid", "https://elsewhere.example/compare", 200),), 1),
        ((), 1),
    ],
)
def test_benchmark_rejects_invalid_config_before_making_requests(cases, repetitions):
    client = FakeClient()
    with pytest.raises(ValueError):
        benchmark(
            client,
            cases,
            repetitions=repetitions,
            clock_ns=lambda: 0,
            setup_seconds=0.0,
            source_commit="pinned123",
        )
    assert client.urls == []
