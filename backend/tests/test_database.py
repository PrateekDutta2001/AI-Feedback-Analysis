"""Database CRUD and filter tests."""

from __future__ import annotations

from backend.app.models.database_models import Feedback
from backend.app.services.feedback_service import apply_filters, create_feedback, delete_feedback, update_feedback
from backend.app.utils.helpers import utcnow


def test_insert_update_delete(db):
    row = create_feedback(
        db,
        {
            "customer_id": "CU-DB-1",
            "text": "Average experience overall, neither good nor bad.",
            "product": "InsightCRM",
            "department": "Product",
            "channel": "Survey",
            "location": "Pune",
            "segment": "SMB",
            "rating": 3,
        },
        user="tester",
        ip="127.0.0.1",
    )
    assert row.id
    updated = update_feedback(db, row.id, {"status": "resolved"}, "tester", "127.0.0.1")
    assert updated.status == "resolved"
    delete_feedback(db, row.id, "tester", "127.0.0.1")
    assert db.query(Feedback).filter(Feedback.id == row.id).first() is None


def test_filtering(db):
    create_feedback(
        db,
        {
            "customer_id": "CU-DB-2",
            "text": "Please add Slack notifications for critical feedback.",
            "product": "InsightChat",
            "department": "Engineering",
            "channel": "Chat",
            "location": "London",
            "segment": "Enterprise",
            "rating": 4,
            "date": utcnow(),
        },
        user="tester",
        ip="127.0.0.1",
    )
    query = apply_filters(db.query(Feedback), {"product": "InsightChat", "channel": "Chat"})
    assert query.count() >= 1
