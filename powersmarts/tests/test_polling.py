from __future__ import annotations

import json

import pytest

from powersmarts.models import DesiredState
from powersmarts.polling import PollError, parse_desired_state, redact_url


def test_parse_on() -> None:
    assert parse_desired_state({"state": "on"}) == DesiredState(power="on")
    assert parse_desired_state({"state": "ON"}) == DesiredState(power="on")


def test_parse_off() -> None:
    assert parse_desired_state({"state": "off"}) == DesiredState(power="off")
    assert parse_desired_state({"state": "Off"}) == DesiredState(power="off")


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        "on",
        {},
        {"state": "maybe"},
        {"mode": "heat", "temperature": 21.5},
        {"state": 1},
    ],
)
def test_parse_invalid_response(payload: object) -> None:
    with pytest.raises(PollError):
        parse_desired_state(payload)


def test_parse_json_string_is_invalid() -> None:
    with pytest.raises(PollError):
        parse_desired_state(json.loads('"on"'))


def test_redact_url_drops_query() -> None:
    assert (
        redact_url("https://example.com/path?token=secret#frag")
        == "https://example.com/path"
    )
