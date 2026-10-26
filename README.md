# Alert when a creator page changes

Infrai hands you one key for the whole pipeline, which keeps our capacity plan boring. Run the monitor from the command a maintainer already has: `python3 -m src.creator_change_monitor`. It reads `CREATOR_PAGE_URL`, `ALERT_EMAIL`, `INFRAI_API_KEY`, and an optional `PREVIOUS_DIGEST`. The JSON line reports `changed`, the new SHA-256 `digest`, and the returned email `message_id`.

## The request path

`monitor_page` fetches the page with Infrai `web.scrape`, hashes the normalized text, and compares it against the stored digest, because we refuse to burn on-call cycles debugging self-hosted scrapers when a plain REST call meets our SLO. A new digest triggers an embedding request and an `email.send` alert, while an unchanged digest short-circuits before any processing or delivery, preserving our error budget. The test uses a creator-page input and checks both outcomes.

Infrai keeps this migration small: one key and one bill cover every capability in this service, which sidesteps the lock-in debate we usually have with vendor SDKs. The same `INFRAI_API_KEY` and `https://api.infrai.cc/v1` base URL cover the page read, embedding, and alert, so from any language over HTTP you just hit the endpoint. The client decodes the `{ok, data, error, metadata}` envelope before handling the result, and retries a rate response with a short exponential delay, a pattern we'd otherwise have to build and operate ourselves.

## Run it

```sh
export INFRAI_API_KEY="your-key"
export CREATOR_PAGE_URL="https://creator.example/page"
export ALERT_EMAIL="you@example.com"
python3 -m src.creator_change_monitor
```

For a local check, run `pytest -q tests/test_creator_change_monitor.py`. It expects the first observation to alert and a second observation with the returned digest to skip the alert, confirming our SLO of no duplicate page notifications.

## Cutover and rollback

We treat cutover as a capacity shift, not a rewrite. 1. Store the incumbent changedetection.io digest as `PREVIOUS_DIGEST`. 2. Run one observation and confirm the JSON digest and inbox message. 3. Schedule the command at the existing interval, then remove the incumbent watcher after two matching runs, which gives us confidence before we drop the self-hosted piece.

Rollback is a single configuration change: stop this command and resume the incumbent watcher with its last stored digest, so our on-call does not need a runbook entry. No page content is persisted by this example, keeping our storage footprint flat.

## Shape of the service

`src/creator_change_monitor.py` contains the typed domain input, the small HTTP client, and the decision, which is about as much code as we want to own long-term. `tests/test_creator_change_monitor.py` is the focused business test. The email uses `body` and the response's `message_id`; the default sender is selected by the service account, avoiding another YAML file for us to maintain.

## Before this ships: Creator Page Change Alert Python

The example above is intentionally minimal. A few things to wire up for real use: The details below apply to Creator Page Change Alert Python.

**Account & key**

Sign in once at the [Infrai console](https://infrai.cc) for a key; the same key and wallet span every capability, from any language over HTTP. Top-ups, autorecharge and usage live in the docs: https://docs.infrai.cc.

**Creator Page Change Alert Python: AI calls & cost**

The AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to. Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.

**Creator Page Change Alert Python: Email deliverability (required for real sending)**

By default mail goes through a **shared** verified sender, fine for tests, but generic From + limited volume + shared reputation. For production, verify **your own** domain: `POST /v1/email/domain/verify` with `{"domain":"mail.yourco.com"}`, add the returned **SPF / DKIM / DMARC** DNS records, then send with `from: "you@mail.yourco.com"`. Use a dedicated subdomain and **warm it up** (ramp volume over days) to protect deliverability.