"""Helper functions to get and set system state flags."""

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_state import SystemState
from app.database import async_session


async def set_state(key: str, value: str):
    """Set or update a system state key-value pair."""
    async with async_session() as db:
        # PostgreSQL UPSERT logic
        stmt = insert(SystemState).values(key=key, value=value)
        stmt = stmt.on_conflict_do_update(
            index_elements=['key'],
            set_={'value': value}
        )
        await db.execute(stmt)
        await db.commit()


async def get_state(key: str, default: str = None) -> str | None:
    """Retrieve a system state value by key."""
    async with async_session() as db:
        result = await db.execute(select(SystemState).where(SystemState.key == key))
        state = result.scalar_one_or_none()
        if state:
            return state.value
        return default

