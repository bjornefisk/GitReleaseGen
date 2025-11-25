import os
import time

import pytest
import requests
import responses

import helixcommit.bitbucket_client as bb_client_module
from helixcommit.bitbucket_client import BitbucketClient, BitbucketSettings


@responses.activate
def test_get_pull_request_parses_response():
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/42",
        json={
            "id": 42,
            "title": "Add payments endpoint",
            "links": {
                "html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/42"}
            },
            "state": "MERGED",
            "closed_on": "2024-05-01T12:34:56Z",
            "author": {"display_name": "John Doe", "nickname": "johndoe"},
            "reviewers": [{"display_name": "Jane Smith", "nickname": "janesmith"}],
            "description": "Implements the new payments endpoint.",
        },
        status=200,
    )

    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo", token="test-token")
    )
    pull = client.get_pull_request(42)
    client.close()

    assert pull is not None
    assert pull.number == 42
    assert pull.title == "Add payments endpoint"
    assert pull.author == "John Doe"
    assert pull.assignees == ["Jane Smith"]
    assert pull.url == "https://bitbucket.org/myworkspace/myrepo/pull-requests/42"


@responses.activate
def test_get_pull_request_returns_none_for_404():
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/999",
        json={"error": {"message": "Pull request not found"}},
        status=404,
    )

    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo")
    )
    pull = client.get_pull_request(999)
    client.close()

    assert pull is None


@responses.activate
def test_find_pull_requests_by_commit_handles_missing():
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/commit/abc123/pullrequests",
        json={"values": []},
        status=200,
    )

    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo")
    )
    pulls = client.find_pull_requests_by_commit("abc123")
    client.close()

    assert pulls == []


@responses.activate
def test_find_pull_requests_by_commit_returns_prs():
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/commit/def456/pullrequests",
        json={
            "values": [
                {
                    "id": 10,
                    "title": "Feature branch",
                    "links": {"html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/10"}},
                    "state": "MERGED",
                    "closed_on": "2024-06-01T10:00:00Z",
                    "author": {"display_name": "Dev User"},
                    "reviewers": [],
                    "description": "A feature PR.",
                }
            ]
        },
        status=200,
    )

    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo")
    )
    pulls = client.find_pull_requests_by_commit("def456")
    client.close()

    assert len(pulls) == 1
    assert pulls[0].number == 10
    assert pulls[0].title == "Feature branch"


@responses.activate
def test_get_pull_request_retries_on_5xx(monkeypatch):
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/99",
        json={"error": {"message": "upstream error"}},
        status=500,
    )
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/99",
        json={
            "id": 99,
            "title": "Stabilize feature flag",
            "links": {"html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/99"}},
            "state": "OPEN",
            "author": {"display_name": "Test User"},
            "reviewers": [],
        },
        status=200,
    )
    monkeypatch.setattr(bb_client_module.random, "random", lambda: 0.5)
    sleep_calls: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo"),
        max_retries=2,
        backoff_base=0.1,
        backoff_cap=0.1,
        sleep_func=fake_sleep,
    )
    pull = client.get_pull_request(99)
    client.close()

    assert pull is not None
    assert pull.number == 99
    assert len(responses.calls) == 2
    assert pytest.approx(sleep_calls, rel=1e-6) == [0.05]


@responses.activate
def test_get_pull_request_retries_on_timeout(monkeypatch):
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/7",
        body=requests.exceptions.Timeout("timeout"),
    )
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/7",
        json={
            "id": 7,
            "title": "Handle network hiccups",
            "links": {"html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/7"}},
            "state": "OPEN",
            "author": {"display_name": "Net User"},
            "reviewers": [],
        },
        status=200,
    )
    monkeypatch.setattr(bb_client_module.random, "random", lambda: 0.25)
    sleep_calls: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo"),
        max_retries=2,
        backoff_base=0.2,
        backoff_cap=0.2,
        sleep_func=fake_sleep,
    )
    pull = client.get_pull_request(7)
    client.close()

    assert pull is not None
    assert pull.number == 7
    assert len(responses.calls) == 2
    assert pytest.approx(sleep_calls, rel=1e-6) == [0.05]


@responses.activate
def test_get_pull_request_respects_retry_after(monkeypatch):
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/101",
        json={"error": {"message": "rate limited"}},
        status=429,
        headers={"Retry-After": "1"},
    )
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/101",
        json={
            "id": 101,
            "title": "Reduce API calls",
            "links": {"html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/101"}},
            "state": "OPEN",
            "author": {"display_name": "Rate User"},
            "reviewers": [],
        },
        status=200,
    )
    sleep_calls: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo"),
        max_retries=2,
        sleep_func=fake_sleep,
    )
    pull = client.get_pull_request(101)
    client.close()

    assert pull is not None
    assert pull.number == 101
    assert len(responses.calls) == 2
    assert pytest.approx(sleep_calls, rel=1e-6) == [1.0]


@responses.activate
def test_disk_cache_serves_pr_from_disk(tmp_path, monkeypatch):
    cache_dir = tmp_path / "bb-cache"
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/5",
        json={
            "id": 5,
            "title": "Cache me if you can",
            "links": {"html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/5"}},
            "state": "OPEN",
            "author": {"display_name": "Cache User"},
            "reviewers": [],
        },
        status=200,
    )
    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo"),
        enable_disk_cache=True,
        cache_dir=cache_dir,
        cache_ttl_seconds=600,
    )
    pull = client.get_pull_request(5)
    client.close()

    assert pull is not None
    assert pull.title == "Cache me if you can"
    assert len(responses.calls) == 1

    # Second client should hit the disk cache; no HTTP stubs remaining.
    client_cached = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo"),
        enable_disk_cache=True,
        cache_dir=cache_dir,
        cache_ttl_seconds=600,
    )
    pull_cached = client_cached.get_pull_request(5)
    client_cached.close()

    assert pull_cached is not None
    assert pull_cached.title == "Cache me if you can"
    assert len(responses.calls) == 1


@responses.activate
def test_disk_cache_expires_after_ttl(tmp_path, monkeypatch):
    cache_dir = tmp_path / "bb-cache-expiring"
    url = "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/88"
    responses.add(
        responses.GET,
        url,
        json={
            "id": 88,
            "title": "Initial title",
            "links": {"html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/88"}},
            "state": "OPEN",
            "author": {"display_name": "TTL User"},
            "reviewers": [],
        },
        status=200,
    )
    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo"),
        enable_disk_cache=True,
        cache_dir=cache_dir,
        cache_ttl_seconds=1,
    )
    first = client.get_pull_request(88)
    client.close()

    assert first is not None
    assert first.title == "Initial title"

    cache_file = cache_dir / "pr" / "myworkspace" / "myrepo" / "88.json"
    assert cache_file.exists()
    stale_time = time.time() - 120
    os.utime(cache_file, (stale_time, stale_time))

    responses.add(
        responses.GET,
        url,
        json={
            "id": 88,
            "title": "Refreshed title",
            "links": {"html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/88"}},
            "state": "OPEN",
            "author": {"display_name": "TTL User"},
            "reviewers": [],
        },
        status=200,
    )
    client_refresh = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo"),
        enable_disk_cache=True,
        cache_dir=cache_dir,
        cache_ttl_seconds=1,
    )
    refreshed = client_refresh.get_pull_request(88)
    client_refresh.close()

    assert refreshed is not None
    assert refreshed.title == "Refreshed title"
    # Two HTTP calls in total for this endpoint (initial + refresh).
    assert sum(1 for call in responses.calls if call.request.url == url) == 2


@responses.activate
def test_batch_pull_requests():
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/1",
        json={
            "id": 1,
            "title": "PR One",
            "links": {"html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/1"}},
            "state": "OPEN",
            "author": {"display_name": "User One"},
            "reviewers": [],
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/2",
        json={
            "id": 2,
            "title": "PR Two",
            "links": {"html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/2"}},
            "state": "MERGED",
            "closed_on": "2024-07-01T10:00:00Z",
            "author": {"display_name": "User Two"},
            "reviewers": [],
        },
        status=200,
    )

    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo")
    )
    results = client.batch_pull_requests([1, 2])
    client.close()

    assert len(results) == 2
    assert results[1].title == "PR One"
    assert results[2].title == "PR Two"


@responses.activate
def test_map_commits_to_prs():
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/commit/sha1/pullrequests",
        json={
            "values": [
                {
                    "id": 10,
                    "title": "PR for sha1",
                    "links": {"html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/10"}},
                    "state": "MERGED",
                    "closed_on": "2024-08-01T10:00:00Z",
                    "author": {"display_name": "User Sha1"},
                    "reviewers": [],
                }
            ]
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/commit/sha2/pullrequests",
        json={"values": []},
        status=200,
    )

    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo")
    )
    mapping = client.map_commits_to_prs(["sha1", "sha2"])
    client.close()

    assert len(mapping["sha1"]) == 1
    assert mapping["sha1"][0].number == 10
    assert mapping["sha2"] == []


@responses.activate
def test_in_memory_cache_prevents_duplicate_requests():
    responses.add(
        responses.GET,
        "https://api.bitbucket.org/2.0/repositories/myworkspace/myrepo/pullrequests/50",
        json={
            "id": 50,
            "title": "Cached in memory",
            "links": {"html": {"href": "https://bitbucket.org/myworkspace/myrepo/pull-requests/50"}},
            "state": "OPEN",
            "author": {"display_name": "Memory User"},
            "reviewers": [],
        },
        status=200,
    )

    client = BitbucketClient(
        BitbucketSettings(workspace="myworkspace", repo_slug="myrepo")
    )
    
    # First call makes HTTP request
    pull1 = client.get_pull_request(50)
    # Second call should use in-memory cache
    pull2 = client.get_pull_request(50)
    client.close()

    assert pull1 is not None
    assert pull2 is not None
    assert pull1.title == pull2.title
    # Only one HTTP call should have been made
    assert len(responses.calls) == 1

