# Powersmarts

Powersmarts is a Home Assistant App that polls a remote [Powersmarts](https://powersmarts.appspot.com/) cloud service and applies the resulting desired state to Home Assistant devices.

The Powersmarts cloud application remains responsible for deciding what devices should be doing. This App runs on a Raspberry Pi with Home Assistant OS and acts as a local gateway:

1. Poll a configured URL.
2. Read the desired state from the response.
3. Ask Home Assistant to apply that state to selected entities.

It does not talk to Matter, Tapo, or other hardware directly. Home Assistant is the local device layer.

## Why it uses polling

Powersmarts in the cloud runs on Google App Engine Standard Environment.
Many home electrical devices (e.g. home heating controls or some Wi-Fi controlled plugs) can only be controlled from the local home network.
Hence Home Assistant can be used to control local devices based on logic automation logic provided by the Powersmarts cloud application.
This Powersmarts Home Assistant app calls out from the home network to the cloud application to check the intended status (e.g. on or off) of the electrical devices and controls them accordingly.

By calling out from the home to the cloud, rather than the cloud trying to connect to the home, users don't need to have a fixed home IP address, do any router configuration, or expose their Home Assistant system to the public internet.

App Engine standard environment doesn't support web sockets, hence this app using HTTP polling.

## Installation

Home Assistant builds the App image locally from the Dockerfile in this repository.

1. Open Home Assistant.
2. Go to **Settings → Apps**.
3. Choose **Install app**.
4. Add this GitHub repository as a custom App repository: `https://github.com/adamalton/ha-apps`
5. Find **Powersmarts**.
6. Install it.
7. Start it.
8. Enable **Start on boot** if it is not already enabled. Enable **Watchdog** so the App restarts if the container dies.
9. Open the Powersmarts web UI.
10. Add a device automation.


## Using a device automation

Each automation has a name, a poll URL, an interval, and one or more Home Assistant switch entities.

Example:

- Name: `Dehumidifier`
- URL: `https://powersmarts.example.com/dehumidifier/state`
- Interval: `5` seconds
- Target: `switch.dehumidifier`

The first version expects:

```json
{"state": "on"}
```

or:

```json
{"state": "off"}
```

A successful `"on"` turns every selected entity on. A successful `"off"` turns every selected entity off. If the entities are already in that state, Powersmarts does not call Home Assistant again. A timeout, HTTP error, or invalid response leaves the devices unchanged.

## Troubleshooting

1. Open **Settings → Apps → Powersmarts**.
2. Open the **Log** tab.
3. Confirm the App started and loaded automations.
4. Set the App option **Log level** to `debug` if you need to see every poll.

The App talks to Home Assistant Core through `http://supervisor/core/api` using the `SUPERVISOR_TOKEN` supplied by Home Assistant. You do not configure a Home Assistant access token.

## Development images

This repository includes a GitHub Actions workflow that runs the Python tests, then builds `aarch64` and `amd64` images. Images are published to GitHub Container Registry only after the tests pass, and only on pushes to `main`. Until those images are public and referenced from `powersmarts/config.yaml`, Home Assistant installs the App by building the Dockerfile locally. That is the supported install path for this version.

Architectures: `aarch64` (Raspberry Pi Home Assistant OS) and `amd64`.
