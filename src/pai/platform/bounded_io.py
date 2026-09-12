"""Request deadlines that don't wait for slow driver cancellation/rollback.

Cancelled operations remain tracked and capped until their cleanup finishes. This
prevents an unavailable database from creating unbounded tasks or blocking login.
"""

import asyncio
import weakref

_pending = weakref.WeakKeyDictionary()


async def run_bounded(factory, timeout: float, *, group: str, max_pending: int = 32):
    loop = asyncio.get_running_loop()
    groups = _pending.setdefault(loop, {})
    tasks = groups.setdefault(group, set())
    if len(tasks) >= max_pending:
        raise TimeoutError("Dependency concurrency budget exhausted")
    task = asyncio.create_task(factory(), name=f"bounded-{group}")
    tasks.add(task)

    def completed(done):
        tasks.discard(done)
        if not done.cancelled():
            done.exception()  # Consume errors from cleanup that outlived its request.

    task.add_done_callback(completed)
    try:
        done, _ = await asyncio.wait({task}, timeout=timeout)
        if not done:
            task.cancel()
            raise TimeoutError("Dependency deadline exceeded")
        return task.result()
    except BaseException:
        if not task.done():
            task.cancel()
        raise


async def close_pending() -> None:
    groups = _pending.get(asyncio.get_running_loop(), {})
    tasks = {task for group in groups.values() for task in group if not task.done()}
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.wait(tasks, timeout=2)
