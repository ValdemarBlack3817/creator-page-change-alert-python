import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from creator_change_monitor import CreatorPage, monitor_page


class StubClient:
    def __init__(self, content: str):
        self.content = content
        self.calls = []

    def scrape(self, url: str) -> str:
        self.calls.append(("scrape", url))
        return self.content

    def embedding(self, text: str) -> list[float]:
        self.calls.append(("embedding", text))
        return [0.1, 0.2]

    def send_alert(self, recipient: str, subject: str, body: str) -> str:
        self.calls.append(("email", recipient, subject, body))
        return "msg_123"


def test_same_digest_skips_processing_and_alert():
    client = StubClient("weekly post")
    first = monitor_page(CreatorPage("https://creator.example/page", "reader@example.com"), client)
    client.calls.clear()

    second = monitor_page(CreatorPage("https://creator.example/page", "reader@example.com", first.digest), client)

    assert first.changed is True
    assert second.changed is False
    assert second.alert_message_id is None
    assert [call[0] for call in client.calls] == ["scrape"]
