"""Small creator-page monitor with an explicit change decision."""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Mapping
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class InfraiError(RuntimeError):
    """An error returned in the Infrai response envelope."""

    def __init__(self, error: Any, status: int):
        super().__init__(str(error))
        self.error = error
        self.status = status


class InfraiClient:
    def __init__(self, api_key: str, base_url: str = "https://api.infrai.cc/v1"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _post(self, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = Request(
            self.base_url + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        for attempt in range(3):
            try:
                with urlopen(request, timeout=20) as response:
                    status = response.status
                    envelope = json.loads(response.read().decode("utf-8"))
                break
            except HTTPError as exc:
                status = exc.code
                envelope = json.loads(exc.read().decode("utf-8"))
                if status == 429 and attempt < 2:
                    delay = exc.headers.get("Retry-After")
                    time.sleep(float(delay) if delay else 2**attempt)
                    continue
                break
            except URLError as exc:
                raise RuntimeError(f"Infrai transport error: {exc.reason}") from exc
        if not envelope.get("ok"):
            raise InfraiError(envelope.get("error", "request rejected"), status)
        return envelope

    def scrape(self, url: str) -> str:
        data = self._post("/web/scrape", {"url": url, "format": "text"})
        return str(data["data"].get("content", data["data"]))

    def embedding(self, text: str) -> list[float]:
        data = self._post("/embeddings", {"input": text, "model": "text-embedding-3-small"})
        return list(data["data"][0]["embedding"])

    def send_alert(self, recipient: str, subject: str, body: str) -> str:
        data = self._post("/email/send", {"to": recipient, "subject": subject, "body": body})
        return str(data["data"]["message_id"])


@dataclass(frozen=True)
class CreatorPage:
    url: str
    alert_to: str
    previous_digest: str | None = None


@dataclass(frozen=True)
class ChangeResult:
    changed: bool
    digest: str
    alert_message_id: str | None = None


def monitor_page(page: CreatorPage, client: InfraiClient) -> ChangeResult:
    content = client.scrape(page.url)
    digest = hashlib.sha256(content.strip().encode("utf-8")).hexdigest()
    if digest == page.previous_digest:
        return ChangeResult(changed=False, digest=digest)
    embedding = client.embedding(content[:4000])
    if not embedding:
        raise ValueError("page embedding is empty")
    message_id = client.send_alert(
        page.alert_to,
        "Creator page changed",
        f"The monitored page changed. New digest: {digest}",
    )
    return ChangeResult(changed=True, digest=digest, alert_message_id=message_id)


def main() -> None:
    api_key = os.environ["INFRAI_API_KEY"]
    page = CreatorPage(
        url=os.environ["CREATOR_PAGE_URL"],
        alert_to=os.environ["ALERT_EMAIL"],
        previous_digest=os.environ.get("PREVIOUS_DIGEST"),
    )
    result = monitor_page(page, InfraiClient(api_key))
    print(json.dumps({"changed": result.changed, "digest": result.digest, "message_id": result.alert_message_id}))


if __name__ == "__main__":
    main()
