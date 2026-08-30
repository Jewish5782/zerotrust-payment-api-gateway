"""Demo API keys. These are lab secrets, not production credentials."""

from __future__ import annotations

# hmac secret is shown in the console so a demo can be replayed by hand
KEYS = {
    "pk_merchant_a": {
        "secret": "sec_merchant_a_lab_only",
        "merchant_id": "MER-A",
        "scopes": {"receive", "send", "balance"},
        "daily_send_limit_ghs": 20000,
        "max_send_ghs": 5000,
    },
    "pk_merchant_b_receive_only": {
        "secret": "sec_merchant_b_lab_only",
        "merchant_id": "MER-B",
        "scopes": {"receive", "balance"},
        "daily_send_limit_ghs": 0,
        "max_send_ghs": 0,
    },
    "pk_merchant_c": {
        "secret": "sec_merchant_c_lab_only",
        "merchant_id": "MER-C",
        "scopes": {"receive", "send", "balance"},
        "daily_send_limit_ghs": 8000,
        "max_send_ghs": 2500,
    },
}
