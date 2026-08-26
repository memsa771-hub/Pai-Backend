"""Write gates. Intelligences propose; this validates; domains persist.

Not a process engine — cross-domain processes live in pai.workflows.
"""

from pai.domains.actions.service import process_task_proposals as accept_actions
from pai.kernel.evidence.vault_apply import process_candidates as accept_vault_candidates
from pai.kernel.evidence.candidate_eval import evaluate_candidates_batch

__all__ = [
    "accept_actions",
    "accept_vault_candidates",
    "evaluate_candidates_batch",
]
