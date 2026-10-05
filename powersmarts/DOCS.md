# Powersmarts

Powersmarts polls a configured cloud URL and tells Home Assistant to turn selected switch entities on or off.

The cloud service decides the desired state. This App is a local gateway.

## Configuration

Open the Powersmarts web UI from the App page in Home Assistant.

For each device automation:

1. Give it a name, such as `Dehumidifier`.
2. Enter the HTTPS URL that returns the desired state.
3. Set how often to poll, in seconds.
4. Choose one or more Home Assistant switch entities.
5. Save and enable the automation.

The first version expects a JSON body of `{"state": "on"}` or `{"state": "off"}`.

If a poll fails, Powersmarts leaves the devices unchanged and retries on the next interval.

## App options

The only App option is **Log level**. Set it to `debug` to log every poll.

Device automations are stored under `/data/powersmarts.json` inside the App container. They are not configured in the standard App options form.

## Troubleshooting

1. Open **Settings → Apps → Powersmarts**.
2. Open the **Log** tab.
3. Look for startup, poll failures, and Home Assistant API errors.

Typical issues:

- The poll URL is unreachable from the home network.
- The URL returns a non-2xx status or a body that is not `{"state": "on"}` / `{"state": "off"}`.
- A selected entity is missing from Home Assistant.
- The App is stopped. Start it, and keep **Start on boot** enabled. Enable **Watchdog** so Home Assistant restarts the App if the container dies.
