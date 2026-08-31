"""MQTT text send for Boss geek chat (adapted from zhipin-geek mqtt_chat).

Reference: https://github.com/DuanXiaoWen/zhipin-geek (boss_cli/mqtt_chat.py)
Auth: page_token|0 + wt2 over WSS; Cookie required for upgrade.
"""

from __future__ import annotations

import logging
import threading
import time

LOG = logging.getLogger("boss-bridge.mqtt")


def _varint(value: int) -> bytes:
    bits = []
    value = int(value)
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            bits.append(b | 0x80)
        else:
            bits.append(b)
            break
    return bytes(bits)


def _field(field_num: int, wire_type: int, data: bytes) -> bytes:
    tag = (field_num << 3) | wire_type
    return _varint(tag) + data


def _field_varint(field_num: int, value: int) -> bytes:
    return _field(field_num, 0, _varint(value))


def _field_bytes(field_num: int, data: bytes) -> bytes:
    return _field(field_num, 2, _varint(len(data)) + data)


def _field_string(field_num: int, s: str) -> bytes:
    return _field_bytes(field_num, s.encode("utf-8"))


def encode_user(uid: int, encrypt_uid: str = "", source: int = 0) -> bytes:
    buf = _field_varint(1, uid)
    if encrypt_uid:
        buf += _field_string(2, encrypt_uid)
    if source:
        buf += _field_varint(7, source)
    return buf


def encode_body(text: str) -> bytes:
    buf = _field_varint(1, 1)
    buf += _field_varint(2, 1)
    buf += _field_string(3, text)
    return buf


def encode_message(
    from_uid: int,
    from_encrypt_uid: str,
    to_uid: int,
    to_encrypt_uid: str,
    text: str,
    temp_id: int,
) -> bytes:
    from_bytes = encode_user(from_uid, from_encrypt_uid)
    to_bytes = encode_user(to_uid, to_encrypt_uid)
    body_bytes = encode_body(text)
    buf = _field_bytes(1, from_bytes)
    buf += _field_bytes(2, to_bytes)
    buf += _field_varint(3, 1)
    buf += _field_varint(4, temp_id)
    buf += _field_varint(11, temp_id)
    buf += _field_bytes(6, body_bytes)
    return buf


def encode_chat_protocol(message_bytes: bytes) -> bytes:
    buf = _field_varint(1, 1)
    buf += _field_bytes(3, message_bytes)
    return buf


def build_text_message(
    from_uid: int,
    from_encrypt_uid: str,
    to_uid: int,
    to_encrypt_uid: str,
    text: str,
) -> bytes:
    temp_id = int(time.time() * 1000)
    msg = encode_message(
        from_uid, from_encrypt_uid, to_uid, to_encrypt_uid, text, temp_id
    )
    return encode_chat_protocol(msg)


class BossMQTTChat:
    """MQTT over WSS client for geek → boss text messages."""

    WS_SERVERS = ["ws6.zhipin.com", "ws.zhipin.com", "ws2.zhipin.com"]
    PORT = 443
    PATH = "/chatws"
    TOPIC = "chat"

    def __init__(
        self,
        page_token: str,
        wt2: str,
        cookies: dict | None = None,
        timeout: float = 12.0,
    ) -> None:
        self._page_token = page_token
        self._wt2 = wt2
        self._cookies = cookies or {}
        self._timeout = timeout
        self._client = None
        self._connected = threading.Event()
        self._error: str | None = None

    def _make_client(self):
        try:
            import paho.mqtt.client as mqtt
        except ImportError as exc:
            raise RuntimeError(
                "paho-mqtt is required for MQTT send. pip install paho-mqtt"
            ) from exc

        import uuid

        client_id = f"ws-{uuid.uuid4().hex[:16].upper()}"
        try:
            client = mqtt.Client(
                callback_api_version=mqtt.CallbackAPIVersion.VERSION1,
                client_id=client_id,
                transport="websockets",
            )
        except AttributeError:
            client = mqtt.Client(client_id=client_id, transport="websockets")

        client.tls_set()
        cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
        client.ws_set_options(
            path=self.PATH,
            headers={
                "Origin": "https://www.zhipin.com",
                "Cookie": cookie_str,
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            },
        )
        client.username_pw_set(
            username=f"{self._page_token}|0",
            password=self._wt2,
        )
        client.on_connect = self._on_connect
        client.on_disconnect = self._on_disconnect
        return client

    def _on_connect(self, client, userdata, flags, rc):  # noqa: ANN001
        if rc == 0:
            LOG.debug("MQTT connected")
            self._connected.set()
        else:
            self._error = f"MQTT connect failed: rc={rc}"
            self._connected.set()

    def _on_disconnect(self, client, userdata, rc):  # noqa: ANN001
        LOG.debug("MQTT disconnected: rc=%d", rc)

    def __enter__(self) -> "BossMQTTChat":
        self._client = self._make_client()
        self._client.connect(self.WS_SERVERS[0], self.PORT, keepalive=25)
        self._client.loop_start()
        if not self._connected.wait(timeout=self._timeout):
            self._client.loop_stop()
            raise RuntimeError(f"MQTT connection timed out after {self._timeout}s")
        if self._error:
            self._client.loop_stop()
            raise RuntimeError(self._error)
        return self

    def __exit__(self, *args: object) -> None:
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None

    def send(
        self,
        from_uid: int,
        from_encrypt_uid: str,
        to_uid: int,
        to_encrypt_uid: str,
        text: str,
    ) -> None:
        if not self._client:
            raise RuntimeError("Not connected. Use as context manager.")
        payload = build_text_message(
            from_uid, from_encrypt_uid, to_uid, to_encrypt_uid, text
        )
        result = self._client.publish(self.TOPIC, payload, qos=1, retain=False)
        result.wait_for_publish(timeout=self._timeout)
        LOG.debug("MQTT published mid=%s", getattr(result, "mid", "?"))
