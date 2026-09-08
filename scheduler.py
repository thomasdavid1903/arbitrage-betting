"""Repeat scans on a timer, within a request budget.

A scanner is only useful if it looks more often than the prices move, but
every scan costs requests and the monthly allowance is small. So the schedule
is explicit about its cost: it refuses to start without a budget, counts down
as it spends, and stops when the budget is gone rather than quietly eating
the month's allowance.

Nothing here places a bet. It records scans and raises alerts for a person
to look at.
"""

import threading
import time
from datetime import datetime, timezone

import oddspapi

# Never allow a schedule faster than this. Prices do not move quickly enough
# to justify it, and the allowance would be gone in an afternoon.
MIN_INTERVAL_SECONDS = 120


class Scheduler:
    """Runs a scan function on an interval until its budget runs out."""

    def __init__(self, scan_fn):
        self._scan = scan_fn
        self._thread = None
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self.state = {
            "running": False,
            "intervalSeconds": None,
            "budget": 0,
            "spent": 0,
            "scans": 0,
            "startedAt": None,
            "lastScanAt": None,
            "nextScanAt": None,
            "lastError": None,
            "alerts": [],
        }

    # -- control ---------------------------------------------------------

    def start(self, api_key, interval_seconds, budget_requests):
        """Begin scanning. Returns (ok, message)."""
        with self._lock:
            if self.state["running"]:
                return False, "already running"

            interval_seconds = int(interval_seconds)
            if interval_seconds < MIN_INTERVAL_SECONDS:
                return False, "interval must be at least %d seconds" % MIN_INTERVAL_SECONDS
            if budget_requests <= 0:
                return False, "set a request budget first"

            self._stop.clear()
            self.state.update({
                "running": True,
                "intervalSeconds": interval_seconds,
                "budget": int(budget_requests),
                "spent": 0,
                "scans": 0,
                "startedAt": _now(),
                "lastError": None,
                "nextScanAt": _now(),
            })
            self._thread = threading.Thread(
                target=self._loop, args=(api_key,), daemon=True
            )
            self._thread.start()
            return True, "started"

    def stop(self):
        self._stop.set()
        with self._lock:
            self.state["running"] = False
            self.state["nextScanAt"] = None
        return True, "stopped"

    # -- loop ------------------------------------------------------------

    def _loop(self, api_key):
        while not self._stop.is_set():
            remaining = self.state["budget"] - self.state["spent"]
            # Stop before a scan that would overrun rather than part-way in.
            if remaining < self.state.get("lastCost", 1):
                self._finish("request budget spent")
                return

            before = oddspapi.request_count[0]
            try:
                payload = self._scan(api_key)
            except Exception as exc:              # noqa: BLE001 - surfaced to the page
                self._finish("scan failed: %s" % exc)
                return

            cost = payload.get("requests") or (oddspapi.request_count[0] - before)
            with self._lock:
                self.state["spent"] += cost
                self.state["lastCost"] = cost
                self.state["scans"] += 1
                self.state["lastScanAt"] = _now()
                self._record_alerts(payload)

            if self.state["budget"] - self.state["spent"] < cost:
                self._finish("request budget spent")
                return

            with self._lock:
                self.state["nextScanAt"] = _now(self.state["intervalSeconds"])
            if self._stop.wait(self.state["intervalSeconds"]):
                break

        self._finish("stopped")

    def _record_alerts(self, payload):
        """Keep the arbitrages worth a person's attention.

        Only markets both books settle the same way: an unchecked one is a
        question, not an alert.
        """
        for row in payload.get("markets") or []:
            if row.get("ruleRisk") != "standard" or row.get("singleBook"):
                continue
            self.state["alerts"].insert(0, {
                "at": _now(),
                "market": row.get("marketName"),
                "fixture": (row.get("home") or "") + " v " + (row.get("away") or ""),
                "ratio": row.get("ratio"),
                "profit": row.get("profit"),
                "total": row.get("total"),
                "books": row.get("books"),
            })
        del self.state["alerts"][60:]

    def _finish(self, reason):
        with self._lock:
            self.state["running"] = False
            self.state["nextScanAt"] = None
            self.state["lastError"] = reason if reason != "stopped" else None
            self.state["stoppedBecause"] = reason


def _now(offset_seconds=0):
    return datetime.fromtimestamp(
        time.time() + offset_seconds, timezone.utc
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")
