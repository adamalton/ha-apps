from powersmarts.models import DeviceAutomation


def make_automation(**overrides: object) -> DeviceAutomation:
    values: dict[str, object] = {
        "id": "auto-1",
        "name": "Dehumidifier",
        "enabled": True,
        "poll_url": "https://powersmarts.example.com/dehumidifier/state",
        "poll_interval_seconds": 5,
        "target_entities": ["switch.dehumidifier"],
    }
    values.update(overrides)
    return DeviceAutomation(**values)  # type: ignore[arg-type]
