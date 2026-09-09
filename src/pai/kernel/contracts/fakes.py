"""In-memory contract adapters for isolated local development; never production."""
from pai.kernel.contracts.vault import VaultSnapshot
from pai.kernel.errors import PersonNotFoundError


class FakeVaultReader:
    def __init__(self, snapshots=()):
        self.snapshots: dict = {row.person_id: row.model_copy(deep=True) for row in snapshots}

    async def get_snapshot(self, person_id) -> VaultSnapshot | None:
        snapshot = self.snapshots.get(person_id)
        return snapshot.model_copy(deep=True) if snapshot else None

    async def lock_revision(self, person_id):
        snapshot = self.snapshots.get(person_id)
        if snapshot is None:
            raise PersonNotFoundError()
        return snapshot.revision
