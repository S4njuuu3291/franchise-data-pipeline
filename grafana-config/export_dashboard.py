"""Export the editable Grafana dashboard to the provisioning directory."""

import json
import os
from pathlib import Path

import requests


GRAFANA_BASE_URL = os.getenv("GRAFANA_BASE_URL", "http://localhost:3000").rstrip("/")
GRAFANA_ADMIN_USER = os.getenv("GRAFANA_ADMIN_USER", "admin")
GRAFANA_ADMIN_PASSWORD = os.getenv("GRAFANA_ADMIN_PASSWORD", "")
DEV_TITLE = os.getenv("GRAFANA_DEV_DASHBOARD_TITLE", "Franchise Pipeline Monitoring")
PROVISIONED_TITLE = os.getenv("GRAFANA_PROVISIONED_DASHBOARD_TITLE", "Franchise Pipeline Monitoring PROD")
PROVISIONED_UID = os.getenv("GRAFANA_PROVISIONED_DASHBOARD_UID", "gx-metadata-pipeline-prod")
OUTPUT_PATH = Path(__file__).parent / "provisioning" / "dashboards" / "data-monitoring.json"
DEV_OUTPUT_PATH = Path(__file__).parent / "dashboards-dev" / "dashboard.json"


def find_dashboard(title: str) -> dict:
    response = requests.get(
        f"{GRAFANA_BASE_URL}/api/search",
        params={"query": title, "type": "dash-db"},
        auth=(GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD),
        timeout=15,
    )
    response.raise_for_status()
    matches = [item for item in response.json() if item.get("title") == title]
    if not matches:
        raise RuntimeError(f'Dashboard tidak ditemukan: "{title}"')
    return matches[0]

def main() -> None:
    if not GRAFANA_ADMIN_PASSWORD:
        raise RuntimeError("GRAFANA_ADMIN_PASSWORD wajib di-set")

    dev = find_dashboard(DEV_TITLE)
    response = requests.get(
        f"{GRAFANA_BASE_URL}/api/dashboards/uid/{dev['uid']}",
        auth=(GRAFANA_ADMIN_USER, GRAFANA_ADMIN_PASSWORD),
        timeout=15,
    )
    response.raise_for_status()
    dashboard = response.json()["dashboard"]

    # Keep a copy of the dashboard exactly as it exists in the DEV/experiment UI.
    DEV_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEV_OUTPUT_PATH.write_text(
        json.dumps(dashboard, indent=2) + "\n", encoding="utf-8"
    )
    print(f'Saved original "{DEV_TITLE}" -> {DEV_OUTPUT_PATH}')

    # Runtime metadata belongs to Grafana's database, not the provisioned file.
    for field in ("id", "version", "folderId", "meta"):
        dashboard.pop(field, None)
    dashboard["uid"] = PROVISIONED_UID
    dashboard["title"] = PROVISIONED_TITLE
    dashboard["editable"] = False

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(dashboard, indent=2) + "\n", encoding="utf-8")
    print(f'Exported "{DEV_TITLE}" -> {OUTPUT_PATH}')


if __name__ == "__main__":
    try:
        main()
    except (requests.RequestException, RuntimeError, KeyError) as exc:
        raise SystemExit(f"Export dashboard gagal: {exc}") from exc
