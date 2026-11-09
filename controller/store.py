"""Persistent audit, decision, and state store backed by SQLite (C12, C13)."""
import json
import sqlite3
from typing import Any, Dict, List, Optional


class AuditStore:
    """Embedded SQLite store for state checkpoints, audit log, and proposal tracking."""

    def __init__(self, db_path: str = "controller_audit.db"):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS checkpoints (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    sim_minute INTEGER NOT NULL,
                    workflow_id TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    version INTEGER NOT NULL,
                    changed_dims TEXT NOT NULL,
                    proposal_id TEXT,
                    approval_id TEXT,
                    rationale TEXT,
                    impact_score REAL,
                    affected_leads INTEGER,
                    dry_run_json TEXT,
                    metrics_before_json TEXT,
                    metrics_after_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS proposals (
                    proposal_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    base_version INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    actor TEXT NOT NULL,
                    created_minute INTEGER NOT NULL,
                    created_ts TEXT NOT NULL,
                    decided_minute INTEGER,
                    decided_ts TEXT,
                    expires_ts TEXT,
                    reasons TEXT,
                    request_json TEXT NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS incidents (
                    incident_id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    incident_type TEXT NOT NULL,
                    detected_ts TEXT NOT NULL,
                    detected_minute INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    details_json TEXT NOT NULL,
                    resolution_json TEXT
                );
            """)
            conn.commit()

    # --- Checkpoints (C13 Crash Recovery) ---
    def get_checkpoint(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._get_conn() as conn:
            cur = conn.execute("SELECT value FROM checkpoints WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else default

    def set_checkpoint(self, key: str, value: str):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO checkpoints (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
                (key, value)
            )
            conn.commit()

    # --- Audit Log (C12) ---
    def record_audit(
        self,
        ts: str,
        sim_minute: int,
        workflow_id: str,
        actor: str,
        version: int,
        changed_dims: List[str],
        proposal_id: Optional[str] = None,
        approval_id: Optional[str] = None,
        rationale: Optional[str] = None,
        impact_score: Optional[float] = None,
        affected_leads: Optional[int] = None,
        dry_run: Optional[Dict[str, Any]] = None,
        metrics_before: Optional[Dict[str, Any]] = None,
        metrics_after: Optional[Dict[str, Any]] = None,
    ):
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT INTO audit_log (
                    ts, sim_minute, workflow_id, actor, version, changed_dims,
                    proposal_id, approval_id, rationale, impact_score, affected_leads,
                    dry_run_json, metrics_before_json, metrics_after_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ts,
                    sim_minute,
                    workflow_id,
                    actor,
                    version,
                    json.dumps(changed_dims),
                    proposal_id,
                    approval_id,
                    rationale,
                    impact_score,
                    affected_leads,
                    json.dumps(dry_run) if dry_run else None,
                    json.dumps(metrics_before) if metrics_before else None,
                    json.dumps(metrics_after) if metrics_after else None,
                ),
            )
            conn.commit()

    def update_audit_metrics_after(self, workflow_id: str, version: int, metrics_after: Dict[str, Any]):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE audit_log SET metrics_after_json = ? WHERE workflow_id = ? AND version = ?",
                (json.dumps(metrics_after), workflow_id, version)
            )
            conn.commit()

    # --- Proposal Lifecycle (C9) ---
    def record_proposal(
        self,
        proposal_id: str,
        workflow_id: str,
        base_version: int,
        actor: str,
        created_minute: int,
        created_ts: str,
        expires_ts: str,
        request: Dict[str, Any],
    ):
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO proposals (
                    proposal_id, workflow_id, base_version, status, actor,
                    created_minute, created_ts, expires_ts, request_json
                ) VALUES (?, ?, ?, 'pending', ?, ?, ?, ?, ?)
                """,
                (
                    proposal_id,
                    workflow_id,
                    base_version,
                    actor,
                    created_minute,
                    created_ts,
                    expires_ts,
                    json.dumps(request),
                ),
            )
            conn.commit()

    def update_proposal_status(
        self,
        proposal_id: str,
        status: str,
        decided_minute: Optional[int] = None,
        decided_ts: Optional[str] = None,
        reasons: Optional[List[str]] = None,
    ):
        with self._get_conn() as conn:
            conn.execute(
                """
                UPDATE proposals
                SET status = ?, decided_minute = ?, decided_ts = ?, reasons = ?
                WHERE proposal_id = ?
                """,
                (status, decided_minute, decided_ts, json.dumps(reasons) if reasons else None, proposal_id),
            )
            conn.commit()

    # --- Incident Tracking (C8) ---
    def record_incident(
        self,
        incident_id: str,
        workflow_id: str,
        incident_type: str,
        detected_ts: str,
        detected_minute: int,
        details: Dict[str, Any],
    ):
        with self._get_conn() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO incidents (
                    incident_id, workflow_id, incident_type, detected_ts,
                    detected_minute, status, details_json
                ) VALUES (?, ?, ?, ?, ?, 'active', ?)
                """,
                (incident_id, workflow_id, incident_type, detected_ts, detected_minute, json.dumps(details)),
            )
            conn.commit()

    def resolve_incident(self, incident_id: str, resolution: Dict[str, Any]):
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE incidents SET status = 'resolved', resolution_json = ? WHERE incident_id = ?",
                (json.dumps(resolution), incident_id)
            )
            conn.commit()

    # --- Query API (C12) ---
    def query_audit_trail(self, workflow_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        query = "SELECT * FROM audit_log"
        params: List[Any] = []
        if workflow_id:
            query += " WHERE workflow_id = ?"
            params.append(workflow_id)
        query += " ORDER BY sim_minute DESC, id DESC LIMIT ?"
        params.append(limit)

        with self._get_conn() as conn:
            cur = conn.execute(query, params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def query_why_workflow_changed(self, workflow_id: str, at_ts_or_version: Any) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            if isinstance(at_ts_or_version, int):
                cur = conn.execute(
                    "SELECT * FROM audit_log WHERE workflow_id = ? AND version = ?",
                    (workflow_id, at_ts_or_version),
                )
            else:
                cur = conn.execute(
                    "SELECT * FROM audit_log WHERE workflow_id = ? AND ts <= ? ORDER BY ts DESC LIMIT 1",
                    (workflow_id, str(at_ts_or_version)),
                )
            row = cur.fetchone()
            return dict(row) if row else None


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Query Controller Audit Trail (C12)")
    parser.add_argument("--db", default="controller_audit.db", help="Path to SQLite audit db")
    parser.add_argument("--workflow", default=None, help="Workflow ID to query")
    parser.add_argument("--version", type=int, default=None, help="Config version to explain")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent changes to show")
    args = parser.parse_args()

    store = AuditStore(args.db)
    if args.version and args.workflow:
        rec = store.query_why_workflow_changed(args.workflow, args.version)
        if rec:
            print("\n" + "="*60)
            print(f"AUDIT RECORD: Workflow '{rec['workflow_id']}' Version {rec['version']}")
            print("="*60)
            print(f"Timestamp:       {rec['ts']} (Sim Minute: {rec['sim_minute']})")
            print(f"Actor:           {rec['actor']}")
            print(f"Approval ID:     {rec['approval_id']}")
            print(f"Proposal ID:     {rec['proposal_id']}")
            print(f"Changed Dims:    {rec['changed_dims']}")
            print(f"Rationale:       {rec['rationale']}")
            print(f"Impact Score:    {rec['impact_score']}")
            print(f"Affected Leads:  {rec['affected_leads']}")
            print("="*60 + "\n")
        else:
            print(f"No audit entry found for workflow '{args.workflow}' at version {args.version}")
    else:
        trail = store.query_audit_trail(args.workflow, limit=args.limit)
        print(f"\nShowing {len(trail)} audit records:")
        for r in trail:
            print(f"[{r['ts']}] {r['workflow_id']} v{r['version']} by {r['actor']} (dims: {r['changed_dims']}) -> {r['rationale']}")


if __name__ == "__main__":
    main()
