from datetime import datetime, timedelta, timezone
from typing import Dict, Any
import requests


class SyncService:
    def __init__(self, db, config: Dict[str, Any]):
        self.db = db
        self.config = config
        self.base_url = config.get("apps_script_url", "").strip()
        self.timeout = config.get("request_timeout_sec", 20)
        self.batch_size = config.get("sync_batch_size", 50)

    def _request(self, method: str, params=None, payload=None):
        if not self.base_url:
            raise RuntimeError("apps_script_url no configurado")
        if method == "GET":
            r = requests.get(self.base_url, params=params, timeout=self.timeout)
        else:
            r = requests.post(self.base_url, json=payload, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def pull_catalogs(self):
        users = self._request("GET", params={"action": "users"}).get("users", [])
        forms = self._request("GET", params={"action": "forms"}).get("forms", [])
        fields = self._request("GET", params={"action": "fields"}).get("fields", [])

        self.db.upsert_users(users)
        self.db.replace_forms_catalog(forms, fields)
        return {
            "users": len(users),
            "forms": len(forms),
            "fields": len(fields),
        }

    def push_pending(self):
        pending = self.db.get_pending_records(limit=self.batch_size)
        if not pending:
            return {"sent": 0, "ok": 0, "errors": 0}

        payload = {
            "action": "push_records",
            "records": [
                {
                    "local_id": r["local_id"],
                    "form_id": r["form_id"],
                    "usuario": r["usuario"],
                    "created_at": r["created_at"],
                    "data": __import__("json").loads(r["payload_json"]),
                }
                for r in pending
            ],
        }
        response = self._request("POST", payload=payload)
        results = response.get("results", [])

        ok, err = 0, 0
        now = datetime.now(timezone.utc)
        delete_after = (now + timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
        synced_at = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        by_id = {x.get("local_id"): x for x in results}
        for r in pending:
            rid = r["local_id"]
            rr = by_id.get(rid, {"ok": False, "error": "Sin respuesta para registro"})
            if rr.get("ok"):
                self.db.mark_synced(rid, synced_at=synced_at, delete_after=delete_after, remote_id=rr.get("remote_id"))
                ok += 1
            else:
                self.db.mark_error(rid, rr.get("error", "Error desconocido"))
                err += 1

        return {"sent": len(pending), "ok": ok, "errors": err}

    def purge_synced(self):
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        purged = self.db.purge_synced_expired(now_iso)
        return {"purged": purged}
