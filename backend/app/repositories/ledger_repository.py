import json
import logging
import re
from pathlib import Path
from typing import List, Optional

from app.schemas.research_runtime import ResearchLedger

logger = logging.getLogger("uvicorn.error")


class LedgerRepository:
    def __init__(self, storage_dir: Optional[Path | str] = None):
        base_dir = Path(storage_dir) if storage_dir else Path(__file__).resolve().parents[2] / "data" / "research_ledgers"
        self.storage_dir = base_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def create(self, ledger: ResearchLedger) -> ResearchLedger:
        path = self.get_storage_path(ledger.ledger_id)
        if path.exists():
            raise ValueError(f"Ledger already exists: {ledger.ledger_id}")
        logger.info(
            "[research-runtime] ledger create ledger_id=%s path=%s task_history=%s evidence_log=%s final_artifacts=%s",
            ledger.ledger_id,
            path,
            len(ledger.task_history),
            len(ledger.evidence_log),
            len(ledger.final_artifacts),
        )
        self._write(path, ledger)
        return ledger

    def get(self, ledger_id: str) -> Optional[ResearchLedger]:
        path = self.get_storage_path(ledger_id)
        if not path.exists():
            logger.info("[research-runtime] ledger not found ledger_id=%s path=%s", ledger_id, path)
            return None
        logger.info("[research-runtime] ledger load ledger_id=%s path=%s", ledger_id, path)
        with path.open("r", encoding="utf-8") as handle:
            return ResearchLedger.model_validate(json.load(handle))

    def update(self, ledger: ResearchLedger) -> ResearchLedger:
        path = self.get_storage_path(ledger.ledger_id)
        logger.info(
            "[research-runtime] ledger update ledger_id=%s path=%s task_history=%s evidence_log=%s final_artifacts=%s",
            ledger.ledger_id,
            path,
            len(ledger.task_history),
            len(ledger.evidence_log),
            len(ledger.final_artifacts),
        )
        self._write(path, ledger)
        return ledger

    def list(self) -> List[ResearchLedger]:
        ledgers: List[ResearchLedger] = []
        for path in sorted(self.storage_dir.glob("*.json")):
            with path.open("r", encoding="utf-8") as handle:
                ledgers.append(ResearchLedger.model_validate(json.load(handle)))
        return ledgers

    def get_storage_path(self, ledger_id: str) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", ledger_id)
        return self.storage_dir / f"{safe_name}.json"

    def _write(self, path: Path, ledger: ResearchLedger) -> None:
        payload = ledger.model_dump(mode="json", exclude_none=True)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
