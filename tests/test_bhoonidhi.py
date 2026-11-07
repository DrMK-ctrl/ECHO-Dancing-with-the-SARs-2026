from datetime import datetime, timezone
import json
from urllib.error import HTTPError

import pytest

from echo.bhoonidhi import BhoonidhiError, authenticate, search_ssar_gcov


class _Response:
    def __init__(self, body):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self, size=-1):
        return self.body[:size]


def test_authentication_returns_bearer_token_without_persisting_credentials():
    seen = {}

    def open_url(request, timeout):
        seen["url"] = request.full_url
        seen["payload"] = json.loads(request.data)
        seen["timeout"] = timeout
        return _Response(b'{"access_token":"secret-token","token_type":"Bearer"}')

    token = authenticate("local-user", "local-password", open_url=open_url)

    assert token == "secret-token"
    assert seen["url"] == "https://bhoonidhi-api.nrsc.gov.in/auth/token"
    assert seen["payload"] == {
        "userId": "local-user",
        "password": "local-password",
        "grant_type": "password",
    }
    assert seen["timeout"] == 30


def test_authentication_does_not_echo_provider_error_body_or_credentials():
    def open_url(_request, timeout):
        assert timeout == 30
        raise HTTPError("https://bhoonidhi-api.nrsc.gov.in/auth/token", 401, "unauthorized", {}, None)

    with pytest.raises(BhoonidhiError, match="HTTP 401") as error:
        authenticate("local-user", "local-password", open_url=open_url)
    assert "local-password" not in str(error.value)


def test_search_requests_only_online_ssar_gcov_and_preserves_raw_features():
    captured = {}
    feature_collection = {
        "type": "FeatureCollection",
        "context": {"returned": 1},
        "features": [{"type": "Feature", "id": "scene-1", "properties": {"Online": "Y"}}],
        "links": [{"rel": "next", "href": "https://bhoonidhi-api.nrsc.gov.in/next"}],
    }

    def open_url(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["payload"] = json.loads(request.data)
        captured["timeout"] = timeout
        return _Response(json.dumps(feature_collection).encode())

    record = search_ssar_gcov(
        "local-token",
        bounds_wgs84=(33.0, -25.0, 34.0, -24.0),
        start="2026-07-01T00:00:00Z",
        end="2026-07-31T23:59:59Z",
        limit=12,
        open_url=open_url,
        now=lambda: datetime(2026, 11, 7, tzinfo=timezone.utc),
    )

    assert captured["url"] == "https://bhoonidhi-api.nrsc.gov.in/data/search"
    assert captured["headers"]["Authorization"] == "Bearer local-token"
    assert captured["payload"]["collections"] == ["NISAR_SSAR_GCOV"]
    assert captured["payload"]["filter"] == {
        "args": [{"property": "Online"}, "Y"],
        "op": "eq",
    }
    assert captured["payload"]["limit"] == 12
    assert captured["timeout"] == 30
    assert record["instrument"] == "S-SAR"
    assert record["feature_collection"] == feature_collection
    assert record["feature_count"] == 1
    assert record["has_next_page"] is True
    assert record["retrieved_at_utc"] == "2026-11-07T00:00:00+00:00"
    assert "access_token" not in json.dumps(record)


@pytest.mark.parametrize(
    ("bounds", "start", "end", "limit"),
    [
        ((181, -25, 182, -24), "2026-07-01T00:00:00Z", "2026-07-02T00:00:00Z", 10),
        ((33, -25, 34, -24), "2026-07-01", "2026-07-02T00:00:00Z", 10),
        ((33, -25, 34, -24), "2026-07-02T00:00:00Z", "2026-07-01T00:00:00Z", 10),
        ((33, -25, 34, -24), "2026-07-01T00:00:00Z", "2026-07-02T00:00:00Z", 501),
    ],
)
def test_search_rejects_invalid_spatial_temporal_or_size_limits(bounds, start, end, limit):
    with pytest.raises(BhoonidhiError):
        search_ssar_gcov("token", bounds_wgs84=bounds, start=start, end=end, limit=limit)


def test_search_rejects_non_feature_collection_response():
    with pytest.raises(BhoonidhiError, match="FeatureCollection"):
        search_ssar_gcov(
            "token",
            bounds_wgs84=(33, -25, 34, -24),
            start="2026-07-01T00:00:00Z",
            end="2026-07-02T00:00:00Z",
            open_url=lambda *_args, **_kwargs: _Response(b'{"type":"Feature"}'),
        )


def test_cli_refuses_to_prompt_for_credentials_without_interactive_terminal(monkeypatch, capsys):
    import echo.cli as cli

    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: False)
    monkeypatch.setattr(cli, "authenticate", lambda *_args, **_kwargs: pytest.fail("must not authenticate"))

    assert cli.main(
        [
            "bhoonidhi-search",
            "--bbox", "33", "-25", "34", "-24",
            "--start", "2026-07-01T00:00:00Z",
            "--end", "2026-07-02T00:00:00Z",
        ]
    ) == 2
    assert "interactive terminal" in capsys.readouterr().err
