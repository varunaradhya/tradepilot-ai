from __future__ import annotations

import os


# Environment variable names are intentionally generic; provider credentials must
# never be committed and this service never returns their values.
BROKER_SANDBOX_ENV = {
    "dhan": ("TRADEPILOT_DHAN_SANDBOX_CLIENT_ID", "TRADEPILOT_DHAN_SANDBOX_ACCESS_TOKEN"),
}


def sandbox_credential_status(broker: str) -> dict:
    name = broker.strip().lower()
    keys = BROKER_SANDBOX_ENV.get(name)
    if keys is None:
        return {"broker": name, "supported": False, "configured": False, "missing": [], "mode": "SANDBOX_READ_ONLY"}
    missing = [key for key in keys if not os.getenv(key, "").strip()]
    return {
        "broker": name,
        "supported": True,
        "configured": not missing,
        "missing": missing,
        "mode": "SANDBOX_READ_ONLY",
        "secret_values_exposed": False,
        "live_execution_allowed": False,
    }
