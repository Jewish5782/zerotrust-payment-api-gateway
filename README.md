# Payment Policy Guard

Laboratory **policy gateway** in front of mock partner payment APIs (`receive`, `send`, `balance`).

Requests are signed, scoped, and limited. Risky payouts go on a hold queue. Funds move only after a reviewer approves. Built as a portfolio lab (Python, FastAPI, SQLite, HTML desk). Not a live payment processor.

## What it does

Partner APIs fail in ordinary ways: a bad HMAC, a replayed nonce, a key used outside its scope, a first-time destination with a large send, a burst of destinations.

This service:

1. Authenticates each call with HMAC-SHA256 over the request body
2. Checks key scope, amount cap, daily send limit, idempotency, and nonce replay
3. Runs fraud rules (new high-value destination, burst / pass-through)
4. Either executes against an in-memory + SQLite ledger, **denies**, or **holds**
5. Lets a reviewer approve or reject a hold
6. Persists requests, holds, ledger balances, and an audit log

## Policy checks

| Check | Effect |
|---|---|
| Unknown API key / bad HMAC | deny |
| Scope mismatch (e.g. receive-only key on `send`) | deny |
| Over max send or daily limit | deny |
| Replay of nonce or idempotency key | deny |
| New destination + high amount | hold |
| Burst / pass-through pattern | hold |
| Clean, in-policy send | execute (ledger moves) |

Lab keys (also printed on the desk):

| API key | Secret | Scopes |
|---|---|---|
| `pk_merchant_a` | `sec_merchant_a_lab_only` | receive, send, balance |
| `pk_merchant_b_receive_only` | `sec_merchant_b_lab_only` | receive, balance |
| `pk_merchant_c` | `sec_merchant_c_lab_only` | receive, send, balance |

These secrets are for the lab only.

## Quick start

Python 3.10+

```bash
git clone https://github.com/Jewish5782/zerotrust-payment-api-gateway.git
cd zerotrust-payment-api-gateway
python3 -m pip install -r requirements.txt
python3 -m uvicorn ztpay.server:app --app-dir src --host 127.0.0.1 --port 8512
```

Or: `bash start.sh`

Open [http://127.0.0.1:8512](http://127.0.0.1:8512)

- Submit a large send to a new destination (desk can sign with the lab secret)
- Watch it land in Holds
- Approve — ledger balances change; reject — they do not

Offline engine check:

```bash
python3 run_demo.py
python3 -m pytest tests -q
```

## HTTP API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Reviewer desk |
| `GET` | `/health` | Liveness |
| `POST` | `/v1/receive` | Credit a wallet |
| `POST` | `/v1/send` | Debit / payout |
| `POST` | `/v1/balance` | Read balance (scoped) |
| `GET` | `/v1/holds` | Open holds |
| `POST` | `/v1/holds/{id}` | `{"decision":"approve"}` \| `reject` |
| `GET` | `/v1/requests` | Recent requests |
| `GET` | `/v1/ledger` | Account balances |

`sign_with_lab_secret: true` on a request tells the lab server to HMAC the body with the key’s demo secret so you can try the desk without computing the signature by hand.

Example hold-then-approve (after the server is up):

```bash
curl -s http://127.0.0.1:8512/v1/send \
  -H 'content-type: application/json' \
  -d '{
    "api_key": "pk_merchant_a",
    "sign_with_lab_secret": true,
    "amount_ghs": 4000,
    "dest_wallet": "W-NEW-DEST-1",
    "src_wallet": "MER-A",
    "idempotency_key": "demo-1",
    "nonce": "n-1",
    "ts": 1725000000
  }'

curl -s http://127.0.0.1:8512/v1/holds
curl -s http://127.0.0.1:8512/v1/holds/1 \
  -H 'content-type: application/json' \
  -d '{"decision":"approve"}'
```

## Layout

```
src/ztpay/         HMAC auth, keys, policies, fraud rules, ledger, FastAPI app
web/index.html     reviewer desk
data/              SQLite ledger + holds (`ztpay.db`)
tests/             scenario decisions + HMAC reject
run_demo.py        canned cases vs expected decision
start.sh           install deps and bind :8512
```

Delete `data/ztpay.db` to reset balances and holds.

## Scope

This is a laboratory prototype for API controls and payout review. It does not talk to a live acquirer, mobile-money switch, or merchant production keys.
