"""Static department import gates. No application imports or database access."""
from __future__ import annotations

import ast
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1] / "src" / "pai"


def imports(tree, module):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for name in node.names:
                yield node.lineno, name.name
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                base = ".".join(module.split(".")[:-node.level] + ([base] if base else []))
            yield node.lineno, base
            for name in node.names:
                yield node.lineno, base + "." + name.name


def forbidden(source, target):
    if source.startswith(("pai.domains.goals.", "pai.intelligences.goals.")):
        if target.startswith("pai.domains.student.") and not target.startswith("pai.domains.student.public"):
            return "Goals must use the public Vault interface"
    if source.startswith("pai.domains.student.") and target.startswith("pai.domains.goals.models"):
        return "Vault must not access Goal ORM"
    if source.startswith(("pai.domains.documents.", "pai.intelligences.documents.")):
        if target.startswith("pai.intelligences.counselor"):
            return "Documents must not depend on Counselor"
        if target.startswith("pai.domains.student.person"):
            return "Documents must use Vault interfaces, not student ORM/services"
    if source.startswith("pai.intelligences.counselor."):
        if target.startswith(("pai.domains.student.person", "pai.domains.goals.models")):
            return "Counselor must not access canonical ORM"
    if source.startswith("pai.kernel.contracts."):
        if target.startswith(("pai.domains.", "pai.intelligences.", "pai.workflows.", "sqlalchemy")):
            return "Contracts must be independent of implementations"
    if source.startswith("pai.domains.memory."):
        if target.startswith("pai.domains.student.") or target.endswith(".VaultCandidate"):
            return "Memory input conversion belongs to student_learning"
    return None


def main():
    failures = set()
    for path in ROOT.rglob("*.py"):
        module = "pai." + ".".join(path.relative_to(ROOT).with_suffix("").parts)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            failures.add(f"{path.relative_to(ROOT)}:{exc.lineno}: {exc.msg}")
            continue
        for line, target in imports(tree, module):
            reason = forbidden(module, target)
            if reason:
                failures.add(f"{path.relative_to(ROOT)}:{line}: {reason}: {target}")
    if failures:
        print("\n".join(sorted(failures)))
        return 1
    print("Department import boundaries passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
