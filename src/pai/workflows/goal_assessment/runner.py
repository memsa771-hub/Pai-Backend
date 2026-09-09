from pai.domains.student.public import VaultReader
from pai.intelligences.goals.worker import process_goal_job


async def process_goal_job_with_vault(session, settings, job, gateway):
    return await process_goal_job(
        session,
        settings,
        job,
        gateway,
        vault_reader=VaultReader(session, settings),
    )
