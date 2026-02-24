# Utility helpers for the API

from sqlalchemy import select

from models.user import User

# Test account emails — these beneficiaries are excluded from admin portal queries.
# They still exist in the DB for login/testing but are hidden from analytics and lists.
TEST_ACCOUNT_EMAILS = {
    "test@gmail.com",
    "admin@rwanda.gov.rw",
}


def test_account_user_ids_subquery():
    """Return a subquery of user IDs belonging to test accounts.

    Usage in a WHERE clause:
        .where(Beneficiary.user_id.not_in(test_account_user_ids_subquery()))
    """
    return select(User.id).where(User.email.in_(TEST_ACCOUNT_EMAILS)).scalar_subquery()
