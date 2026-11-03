from uuid import UUID, uuid4

from django.core import signing


SALT = "service_logs.unscheduled_submission.v1"
CONSTRAINT = "unique_service_log_submission"


class SavedSubmissionRace(Exception):
    pass


def read_submission_key(token, worker):
    value = signing.Signer(salt=SALT).unsign_object(token)
    if not isinstance(value, dict) or value.get("worker") != worker.pk:
        raise signing.BadSignature("Submission owner does not match.")
    return UUID(value["key"])


def remember_submission(request, worker, token):
    request.session[f"unscheduled_submission:{worker.pk}"] = token


def resume_submission(request, worker, *, new=False):
    session_key = f"unscheduled_submission:{worker.pk}"
    token = request.session.get(session_key)
    if token and not new:
        try:
            read_submission_key(token, worker)
            return token
        except (signing.BadSignature, ValueError, TypeError, KeyError):
            pass
    token = signing.Signer(salt=SALT).sign_object({"worker": worker.pk, "key": str(uuid4())})
    remember_submission(request, worker, token)
    return token


def is_submission_key_conflict(error):
    cause = error.__cause__
    if getattr(getattr(cause, "diag", None), "constraint_name", None) == CONSTRAINT:
        return True
    return (
        getattr(cause, "sqlite_errorname", None) == "SQLITE_CONSTRAINT_UNIQUE"
        and str(cause) == "UNIQUE constraint failed: service_logs_servicelog.submission_key"
    )
