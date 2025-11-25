import os
import time

import pytest
import requests
import responses

import helixcommit.gitlab_client as gl_client_module
from helixcommit.gitlab_client import GitLabClient, GitLabSettings


@responses.activate
def test_get_merge_request_parses_response():
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/42",
        json={
            "iid": 42,
            "title": "Add payments endpoint",
            "web_url": "https://gitlab.com/example/project/-/merge_requests/42",
            "merged_at": "2024-05-01T12:34:56Z",
            "author": {"username": "octocat"},
            "labels": ["feature"],
            "assignees": [{"username": "reviewer"}],
            "description": "Implements the new payments endpoint.",
        },
        status=200,
    )

    client = GitLabClient(GitLabSettings(project_path="example/project", token="test-token"))
    mr = client.get_merge_request(42)
    client.close()

    assert mr is not None
    assert mr.number == 42
    assert mr.title == "Add payments endpoint"
    assert mr.author == "octocat"
    assert mr.labels == ["feature"]


@responses.activate
def test_find_merge_requests_by_commit_handles_missing():
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/repository/commits/abc123/merge_requests",
        json=[],
        status=200,
    )

    client = GitLabClient(GitLabSettings(project_path="example/project"))
    mrs = client.find_merge_requests_by_commit("abc123")
    client.close()

    assert mrs == []


@responses.activate
def test_get_merge_request_returns_none_on_404():
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/999",
        json={"message": "404 Not found"},
        status=404,
    )

    client = GitLabClient(GitLabSettings(project_path="example/project"))
    mr = client.get_merge_request(999)
    client.close()

    assert mr is None


@responses.activate
def test_get_merge_request_retries_on_5xx(monkeypatch):
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/99",
        json={"message": "upstream error"},
        status=500,
    )
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/99",
        json={
            "iid": 99,
            "title": "Stabilize feature flag",
            "web_url": "https://gitlab.com/example/project/-/merge_requests/99",
        },
        status=200,
    )
    monkeypatch.setattr(gl_client_module.random, "random", lambda: 0.5)
    sleep_calls: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    client = GitLabClient(
        GitLabSettings(project_path="example/project"),
        max_retries=2,
        backoff_base=0.1,
        backoff_cap=0.1,
        sleep_func=fake_sleep,
    )
    mr = client.get_merge_request(99)
    client.close()

    assert mr is not None
    assert mr.number == 99
    assert len(responses.calls) == 2
    assert pytest.approx(sleep_calls, rel=1e-6) == [0.05]


@responses.activate
def test_get_merge_request_retries_on_timeout(monkeypatch):
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/7",
        body=requests.exceptions.Timeout("timeout"),
    )
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/7",
        json={
            "iid": 7,
            "title": "Handle network hiccups",
            "web_url": "https://gitlab.com/example/project/-/merge_requests/7",
        },
        status=200,
    )
    monkeypatch.setattr(gl_client_module.random, "random", lambda: 0.25)
    sleep_calls: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    client = GitLabClient(
        GitLabSettings(project_path="example/project"),
        max_retries=2,
        backoff_base=0.2,
        backoff_cap=0.2,
        sleep_func=fake_sleep,
    )
    mr = client.get_merge_request(7)
    client.close()

    assert mr is not None
    assert mr.number == 7
    assert len(responses.calls) == 2
    assert pytest.approx(sleep_calls, rel=1e-6) == [0.05]


@responses.activate
def test_get_merge_request_respects_retry_after(monkeypatch):
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/101",
        json={"message": "rate limited"},
        status=429,
        headers={"Retry-After": "1"},
    )
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/101",
        json={
            "iid": 101,
            "title": "Reduce API calls",
            "web_url": "https://gitlab.com/example/project/-/merge_requests/101",
        },
        status=200,
    )
    sleep_calls: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    client = GitLabClient(
        GitLabSettings(project_path="example/project"),
        max_retries=2,
        sleep_func=fake_sleep,
    )
    mr = client.get_merge_request(101)
    client.close()

    assert mr is not None
    assert mr.number == 101
    assert len(responses.calls) == 2
    assert pytest.approx(sleep_calls, rel=1e-6) == [1.0]


@responses.activate
def test_get_merge_request_handles_rate_limit_reset(monkeypatch):
    fixed_now = 1_700_000_000.0
    monkeypatch.setattr(gl_client_module.time, "time", lambda: fixed_now)
    monkeypatch.setattr(gl_client_module.random, "random", lambda: 0.5)
    reset_at = int(fixed_now) + 3
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/55",
        json={"message": "rate limited"},
        status=403,
        headers={"RateLimit-Remaining": "0", "RateLimit-Reset": str(reset_at)},
    )
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/55",
        json={
            "iid": 55,
            "title": "Respect rate limits",
            "web_url": "https://gitlab.com/example/project/-/merge_requests/55",
        },
        status=200,
    )
    sleep_calls: list[float] = []

    def fake_sleep(delay: float) -> None:
        sleep_calls.append(delay)

    client = GitLabClient(
        GitLabSettings(project_path="example/project"),
        max_retries=2,
        sleep_func=fake_sleep,
    )
    mr = client.get_merge_request(55)
    client.close()

    assert mr is not None
    assert mr.number == 55
    assert len(responses.calls) == 2
    assert pytest.approx(sleep_calls, rel=1e-6) == [3.0]


@responses.activate
def test_disk_cache_serves_mr_from_disk(tmp_path, monkeypatch):
    cache_dir = tmp_path / "gl-cache"
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/5",
        json={
            "iid": 5,
            "title": "Cache me if you can",
            "web_url": "https://gitlab.com/example/project/-/merge_requests/5",
        },
        status=200,
    )
    client = GitLabClient(
        GitLabSettings(project_path="example/project"),
        enable_disk_cache=True,
        cache_dir=cache_dir,
        cache_ttl_seconds=600,
    )
    mr = client.get_merge_request(5)
    client.close()

    assert mr is not None
    assert mr.title == "Cache me if you can"
    assert len(responses.calls) == 1

    # Second client should hit the disk cache; no HTTP stubs remaining.
    client_cached = GitLabClient(
        GitLabSettings(project_path="example/project"),
        enable_disk_cache=True,
        cache_dir=cache_dir,
        cache_ttl_seconds=600,
    )
    mr_cached = client_cached.get_merge_request(5)
    client_cached.close()

    assert mr_cached is not None
    assert mr_cached.title == "Cache me if you can"
    assert len(responses.calls) == 1


@responses.activate
def test_disk_cache_expires_after_ttl(tmp_path, monkeypatch):
    cache_dir = tmp_path / "gl-cache-expiring"
    url = "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/88"
    responses.add(
        responses.GET,
        url,
        json={
            "iid": 88,
            "title": "Initial title",
            "web_url": "https://gitlab.com/example/project/-/merge_requests/88",
        },
        status=200,
    )
    client = GitLabClient(
        GitLabSettings(project_path="example/project"),
        enable_disk_cache=True,
        cache_dir=cache_dir,
        cache_ttl_seconds=1,
    )
    first = client.get_merge_request(88)
    client.close()

    assert first is not None
    assert first.title == "Initial title"

    cache_file = cache_dir / "mr" / "example/project" / "88.json"
    assert cache_file.exists()
    stale_time = time.time() - 120
    os.utime(cache_file, (stale_time, stale_time))

    responses.add(
        responses.GET,
        url,
        json={
            "iid": 88,
            "title": "Refreshed title",
            "web_url": "https://gitlab.com/example/project/-/merge_requests/88",
        },
        status=200,
    )
    client_refresh = GitLabClient(
        GitLabSettings(project_path="example/project"),
        enable_disk_cache=True,
        cache_dir=cache_dir,
        cache_ttl_seconds=1,
    )
    refreshed = client_refresh.get_merge_request(88)
    client_refresh.close()

    assert refreshed is not None
    assert refreshed.title == "Refreshed title"
    # Two HTTP calls in total for this endpoint (initial + refresh).
    assert sum(1 for call in responses.calls if call.request.url == url) == 2


@responses.activate
def test_find_merge_requests_by_commit_returns_multiple():
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/repository/commits/abc123/merge_requests",
        json=[
            {
                "iid": 10,
                "title": "First MR",
                "web_url": "https://gitlab.com/example/project/-/merge_requests/10",
                "author": {"username": "user1"},
            },
            {
                "iid": 11,
                "title": "Second MR",
                "web_url": "https://gitlab.com/example/project/-/merge_requests/11",
                "author": {"username": "user2"},
            },
        ],
        status=200,
    )

    client = GitLabClient(GitLabSettings(project_path="example/project"))
    mrs = client.find_merge_requests_by_commit("abc123")
    client.close()

    assert len(mrs) == 2
    assert mrs[0].number == 10
    assert mrs[0].title == "First MR"
    assert mrs[1].number == 11
    assert mrs[1].title == "Second MR"


@responses.activate
def test_batch_merge_requests():
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/1",
        json={
            "iid": 1,
            "title": "MR One",
            "web_url": "https://gitlab.com/example/project/-/merge_requests/1",
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/2",
        json={
            "iid": 2,
            "title": "MR Two",
            "web_url": "https://gitlab.com/example/project/-/merge_requests/2",
        },
        status=200,
    )
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/merge_requests/3",
        json={"message": "404 Not found"},
        status=404,
    )

    client = GitLabClient(GitLabSettings(project_path="example/project"))
    results = client.batch_merge_requests([1, 2, 3])
    client.close()

    assert len(results) == 2
    assert 1 in results
    assert 2 in results
    assert 3 not in results
    assert results[1].title == "MR One"
    assert results[2].title == "MR Two"


@responses.activate
def test_map_commits_to_mrs():
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/repository/commits/sha1/merge_requests",
        json=[
            {
                "iid": 100,
                "title": "MR for sha1",
                "web_url": "https://gitlab.com/example/project/-/merge_requests/100",
            }
        ],
        status=200,
    )
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/example%2Fproject/repository/commits/sha2/merge_requests",
        json=[],
        status=200,
    )

    client = GitLabClient(GitLabSettings(project_path="example/project"))
    mapping = client.map_commits_to_mrs(["sha1", "sha2"])
    client.close()

    assert len(mapping) == 2
    assert len(mapping["sha1"]) == 1
    assert mapping["sha1"][0].number == 100
    assert len(mapping["sha2"]) == 0


@responses.activate
def test_custom_api_url():
    responses.add(
        responses.GET,
        "https://gitlab.example.com/api/v4/projects/mygroup%2Fmyproject/merge_requests/1",
        json={
            "iid": 1,
            "title": "Self-hosted MR",
            "web_url": "https://gitlab.example.com/mygroup/myproject/-/merge_requests/1",
        },
        status=200,
    )

    client = GitLabClient(
        GitLabSettings(
            project_path="mygroup/myproject",
            api_url="https://gitlab.example.com/api/v4",
            token="test-token",
        )
    )
    mr = client.get_merge_request(1)
    client.close()

    assert mr is not None
    assert mr.number == 1
    assert mr.title == "Self-hosted MR"


@responses.activate
def test_subgroup_project_path():
    # Test project paths with subgroups like group/subgroup/project
    responses.add(
        responses.GET,
        "https://gitlab.com/api/v4/projects/group%2Fsubgroup%2Fproject/merge_requests/1",
        json={
            "iid": 1,
            "title": "Subgroup MR",
            "web_url": "https://gitlab.com/group/subgroup/project/-/merge_requests/1",
        },
        status=200,
    )

    client = GitLabClient(GitLabSettings(project_path="group/subgroup/project"))
    mr = client.get_merge_request(1)
    client.close()

    assert mr is not None
    assert mr.number == 1
    assert mr.title == "Subgroup MR"


def test_private_token_header():
    """Test that the PRIVATE-TOKEN header is set correctly."""
    client = GitLabClient(GitLabSettings(project_path="example/project", token="my-secret-token"))
    assert client._session.headers.get("PRIVATE-TOKEN") == "my-secret-token"
    client.close()


def test_no_token_header_when_none():
    """Test that no PRIVATE-TOKEN header is set when token is None."""
    client = GitLabClient(GitLabSettings(project_path="example/project"))
    assert "PRIVATE-TOKEN" not in client._session.headers
    client.close()

