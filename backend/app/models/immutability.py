from sqlalchemy import event


class ImmutableRecordError(RuntimeError):
    """Raised when application code attempts to update or delete a row, via the ORM, on a
    table that is immutable or append-only by design — see `ProgrammeDecisionImmutableError`
    (app/models/programme_decision.py) for the original precedent this generalizes.

    Honest scope note, same as that precedent: this enforces the application's own ORM path
    only. A database administrator running raw SQL directly is not stopped by this.
    """


def enforce_immutable(model_cls):
    """Registers before_update/before_delete mapper events on `model_cls` that raise
    `ImmutableRecordError`. Every immutable or append-only table introduced by Program Engine
    v5 Milestone 1B calls this once, right after its class definition, instead of each
    hand-writing its own pair of listener functions.
    """

    @event.listens_for(model_cls, "before_update")
    def _reject_update(mapper, connection, target, _cls=model_cls):
        raise ImmutableRecordError(
            f"{_cls.__name__} rows are immutable/append-only and cannot be updated once created "
            f"(id={getattr(target, 'id', '?')!r})."
        )

    @event.listens_for(model_cls, "before_delete")
    def _reject_delete(mapper, connection, target, _cls=model_cls):
        raise ImmutableRecordError(
            f"{_cls.__name__} rows are immutable/append-only and cannot be deleted "
            f"(id={getattr(target, 'id', '?')!r})."
        )
