# Notifications

```python
from reusable_foundations.jobs import Jobs
from reusable_foundations.messaging import Notifications

jobs = Jobs(store)
notifications = Notifications(store, jobs)
notifications.preferences(user_id, ["in_app", "email"])
notice = notifications.publish(user_id, "welcome", {"name": "Member"},
    key="welcome:" + user_id, channels=["in_app", "email"])
inbox = notifications.inbox(user_id)
notifications.mark_read(user_id, notice["id"])
```

Inbox and read operations are owner-scoped. Obtain user_id from authenticated context; never let the browser select another recipient's inbox. Publishing is a trusted server API. Application code resolves domain audiences; the toolkit has no trip/team/all-users broadcast rules.

External selected channels become `notification:email`, `notification:whatsapp`, or other explicitly supplied job kinds. Register each real channel handler in Jobs. There is no implicit WhatsApp/SMS provider; inject an implementation that honors your recipient policy. Channel preferences filter external jobs. Every publication creates an in-app row; external preferences do not suppress that audit of the notice.

`run_at=` hides a scheduled inbox row until due and schedules external jobs. Repeating publication repairs the gap between inbox persistence and enqueue without duplicating matching jobs. Inbox/job writes are not one transaction, and an application that never retries or reconciles a crash can leave external delivery unqueued. Implement a reconciliation loop if delivery is required.

Templates/variables are stored, not HTML-rendered. Escape rendered content in custom consumers. Delivery status, read receipts from external providers, quiet hours, critical-message overrides, digesting, schedule editing/cancellation and unsubscribe compliance need host policies. Preferences are selected at publication; handlers should recheck current preferences before delayed delivery when required.
