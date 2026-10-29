# Background jobs

```python
from reusable_foundations.jobs import Jobs

jobs = Jobs(store)
jobs.enqueue("generate_report", {"report_id": "report-1"}, key="report-1", max_attempts=3)
def generate(payload, job_id):
    # Deduplicate the report/output by job_id before externally visible work.
    create_report_once(payload["report_id"], job_id)
jobs.run_once({"generate_report": generate})
```

Run `run_once` from a host-owned worker loop with backoff when idle, graceful shutdown and monitoring. It handles one due job, returns False when none are available, and propagates handler failures after recording retry state. The toolkit does not launch background threads automatically.

`enqueue(kind,payload,key=...,run_at=...)` uses kind/key identity and rejects changed payloads for the same key. `run_at` is an epoch time. Claims take a random lease token and increment attempts. An expired running job can be reclaimed; stale worker tokens cannot mark a newer claim complete. Retries use capped exponential delay; exhausted jobs remain failed for inspection. Job errors are not automatically logged with potentially sensitive payloads.

Default lease is 60 seconds. `run_once` handlers must finish within that lease. For longer tasks, use `claim(lease_seconds=...)` and `finish(...)` directly, choosing a realistic bound or implementing lease renewal in a future adapter. An expired handler may still run externally while another worker retries: jobs are **at least once**. Use provider idempotency or a transactional application outbox and deduplicated effects. DB leases alone do not guarantee exactly-once delivery.

Schedule edit/cancel UI, recurring cron planner, payload encryption, retention, operational repair and queue dashboards are application extensions. State transitions are covered by offline tests; production crash recovery is not certified.
