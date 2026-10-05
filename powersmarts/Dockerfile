# https://developers.home-assistant.io/docs/apps/configuration#app-dockerfile
FROM ghcr.io/home-assistant/base-python:3.13-alpine3.24

WORKDIR /opt/powersmarts

COPY requirements.txt /opt/powersmarts/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r /opt/powersmarts/requirements.txt

COPY powersmarts /opt/powersmarts/powersmarts
COPY run.sh /run.sh
COPY rootfs /

RUN chmod a+x /run.sh \
    && chmod a+x /etc/services.d/powersmarts/run \
    && chmod a+x /etc/services.d/powersmarts/finish

ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/powersmarts

LABEL \
  io.hass.name="Powersmarts" \
  io.hass.description="Poll a Powersmarts cloud URL and apply the desired state to Home Assistant devices." \
  io.hass.type="app" \
  io.hass.version="0.1.0" \
  io.hass.arch="aarch64|amd64" \
  org.opencontainers.image.title="Powersmarts" \
  org.opencontainers.image.description="Poll a Powersmarts cloud URL and apply the desired state to Home Assistant devices." \
  org.opencontainers.image.source="https://github.com/adamalton/ha-apps" \
  org.opencontainers.image.licenses="MIT"
