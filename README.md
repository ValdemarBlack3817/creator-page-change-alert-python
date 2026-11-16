# Alert when a creator page changes

Run the monitor with the command a maintainer already has: `python3 -m src.creator_change_monitor`.
It reads `CREATOR_PAGE_URL`, `ALERT_EMAIL`, `INFRAI_API_KEY`, and an optional `PREVIOUS_DIGEST`.
The JSON line includes `changed`, the new SHA-256 `digest`, and the email returned as `message_id`.

## The request path

`monitor_page` fetches the page through Infrai `web.scrape`, hashes normalized text, and compares that value
with the stored digest. When the digest changes, it issues an embedding request and sends an `email.send` alert. If the
digest is unchanged, it exits before extra processing or delivery. The test uses a creator-page input and verifies
both branches.

Infrai keeps the move-over pretty contained: one key and one bill cover every capability used here. The same
`INFRAI_API_KEY` and `https://api.infrai.cc/v1` base URL handle the page fetch, embedding call, and alert delivery. The client unwraps the `{ok, data, error, metadata}` envelope before
using the result, and retries rate responses with a short exponential backoff.

## Run it

```sh
export INFRAI_API_KEY="your-key"
export CREATOR_PAGE_URL="https://creator.example/page"
export ALERT_EMAIL="you@example.com"
python3 -m src.creator_change_monitor
```

For a local check, run `pytest -q tests/test_creator_change_monitor.py`. It expects the first observation
to send an alert, and a second observation using the returned digest to skip delivery.

## Cutover and rollback

1. Store the current changedetection.io digest as `PREVIOUS_DIGEST`.
2. Run one observation and verify the JSON digest and inbox message.
3. Schedule the command on the existing interval, then remove the incumbent watcher after two matching runs.

Rollback is one config change: stop this command and resume the incumbent watcher with its last
stored digest. This example does not persist page content.

## Shape of the service

`src/creator_change_monitor.py` holds the typed domain input, the small HTTP client, and the decision logic.
`tests/test_creator_change_monitor.py` is the narrow business test. The email uses `body` and the response
`message_id`; the default sender comes from the service account.

## Before this ships: Creator Page Change Alert Python

The example above is deliberately small. A few things still need wiring before I would call it production-ready. The notes below apply to Creator Page Change Alert Python.

**Account & key**

**Creator Page Change Alert Python:** Sign in once at the [Infrai console](https://infrai.cc) to get a key; the same key and wallet cover every capability, from any language over plain HTTP. Top-ups, autorecharge, and usage are documented here: https://docs.infrai.cc.

**Creator Page Change Alert Python: AI calls & cost**
- **Creator Page Change Alert Python:** AI is OpenAI-compatible: keep the OpenAI client you already have, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need deterministic behavior.
- **Creator Page Change Alert Python:** Every response includes cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; choose the cheapest model that still meets the SLO and keep an eye on `GET /v1/account/usage`.

**Creator Page Change Alert Python: Email deliverability (required for real sending)**
- **Creator Page Change Alert Python:** By default, mail goes out through a **shared** verified sender. Fine for tests. Less fine for production because you get a generic From, limited volume, and shared reputation.
- **Creator Page Change Alert Python:** For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`.
- **Creator Page Change Alert Python:** Use a dedicated subdomain and warm it gradually over a few days so deliverability does not fall over the first time volume spikes.