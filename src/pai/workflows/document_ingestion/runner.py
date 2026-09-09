from pai.domains.student.public import VaultReader, VaultWriter
from pai.intelligences.documents.pipeline import run_document_analysis


async def run_document_analysis_with_vault(
    session, settings, job, *, storage, gateway
):
    return await run_document_analysis(
        session,
        settings,
        job,
        storage=storage,
        gateway=gateway,
        vault_reader=VaultReader(session, settings),
        vault_writer=VaultWriter(session),
    )
