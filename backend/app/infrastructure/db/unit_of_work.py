"""SQLite Unit of Work — the transaction boundary adapter.

Implements `backend.app.domain.ports.UnitOfWork`. The application layer decides
*where* a transaction starts and ends (clean_code_spec 6.2); this class only
supplies the mechanism, holding one `Session` and the repositories bound to it
so that the six steps of an allocation commit or roll back as one unit.

Exiting without an explicit `commit()` rolls back. Anything that leaves the
block early — a typed eligibility failure, an unexpected exception, an early
`return` — must not leave half an allocation behind.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.domain.ports import (
    AcceptanceRepository,
    AgentRunRepository,
    AuditRepository,
    CommunityRepository,
    DeliveryRepository,
    DonationRepository,
    DriverRepository,
)
from backend.app.infrastructure.db.repositories import (
    SqlAlchemyAcceptanceRepository,
    SqlAlchemyAgentRunRepository,
    SqlAlchemyAuditRepository,
    SqlAlchemyCommunityRepository,
    SqlAlchemyDeliveryRepository,
    SqlAlchemyDonationRepository,
    SqlAlchemyDriverRepository,
)
from backend.app.infrastructure.db.session import SessionFactory


class SqlAlchemyUnitOfWork:
    """One transaction, one session, one set of repositories."""

    # Declared as the port types, not the concrete classes, so that assigning an
    # instance to a `UnitOfWork`-typed parameter type-checks. Protocol members
    # are invariant; narrowing these to the SQLAlchemy classes would break it.
    donations: DonationRepository
    communities: CommunityRepository
    drivers: DriverRepository
    deliveries: DeliveryRepository
    acceptances: AcceptanceRepository
    audit: AuditRepository
    # Not part of the UnitOfWork port, but the Agent layer needs to append state
    # events inside the same transaction that creates the delivery order.
    agent_runs: AgentRunRepository

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None

    def __enter__(self) -> SqlAlchemyUnitOfWork:
        session = self._session_factory()
        self._session = session
        self.donations = SqlAlchemyDonationRepository(session)
        self.communities = SqlAlchemyCommunityRepository(session)
        self.drivers = SqlAlchemyDriverRepository(session)
        self.deliveries = SqlAlchemyDeliveryRepository(session)
        self.acceptances = SqlAlchemyAcceptanceRepository(session)
        self.agent_runs = SqlAlchemyAgentRunRepository(session)
        self.audit = SqlAlchemyAuditRepository(session, self._session_factory)
        return self

    def __exit__(self, *args: object) -> None:
        """Roll back anything uncommitted, then release the connection.

        The exception triple is not inspected: an uncommitted unit of work is
        rolled back whether it is leaving through an exception or through a
        plain `return`. A committed one has nothing left to roll back.
        """
        session = self._require_session()
        try:
            session.rollback()
        finally:
            session.close()
            self._session = None

    def commit(self) -> None:
        self._require_session().commit()

    def rollback(self) -> None:
        self._require_session().rollback()

    @property
    def session(self) -> Session:
        """The live session. For the seed runner and integration tests only."""
        return self._require_session()

    def _require_session(self) -> Session:
        if self._session is None:
            raise RuntimeError("SqlAlchemyUnitOfWork used outside a `with` block")
        return self._session
