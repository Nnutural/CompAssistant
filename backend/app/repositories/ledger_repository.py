import json
import logging
import os
import re
import threading
import time
from uuid import uuid4
from pathlib import Path
from typing import List, Optional

from app.schemas.research_runtime import ResearchLedger

logger = logging.getLogger("uvicorn.error")


class LedgerRepository:
    def __init__(self, storage_dir: Optional[Path | str] = None):
        base_dir = Path(storage_dir) if storage_dir else Path(__file__).resolve().parents[2] / "data" / "research_ledgers"
        self.storage_dir = base_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()

    def create(self, ledger: ResearchLedger) -> ResearchLedger:
        path = self.get_storage_path(ledger.ledger_id)
        with self._write_lock:
            if path.exists():
                raise ValueError(f"Ledger already exists: {ledger.ledger_id}")
            logger.info(
                "[research-runtime] ledger create ledger_id=%s path=%s task_history=%s evidence_log=%s events=%s artifacts=%s final_artifacts=%s",
                ledger.ledger_id,
                path,
                len(ledger.task_history),
                len(ledger.evidence_log),
                len(ledger.events),
                len(ledger.artifacts),
                len(ledger.final_artifacts),
            )
            self._write(path, ledger)
        return ledger

    def get(self, ledger_id: str) -> Optional[ResearchLedger]:
        path = self.get_storage_path(ledger_id)
        with self._write_lock:
            if not path.exists():
                logger.info("[research-runtime] ledger not found ledger_id=%s path=%s", ledger_id, path)
                return None
            logger.info("[research-runtime] ledger load ledger_id=%s path=%s", ledger_id, path)
            with path.open("r", encoding="utf-8") as handle:
                return ResearchLedger.model_validate(json.load(handle))

    def update(self, ledger: ResearchLedger) -> ResearchLedger:
        path = self.get_storage_path(ledger.ledger_id)
        with self._write_lock:
            logger.info(
                "[research-runtime] ledger update ledger_id=%s path=%s task_history=%s evidence_log=%s events=%s artifacts=%s final_artifacts=%s state=%s",
                ledger.ledger_id,
                path,
                len(ledger.task_history),
                len(ledger.evidence_log),
                len(ledger.events),
                len(ledger.artifacts),
                len(ledger.final_artifacts),
                ledger.current_state,
            )
            self._write(path, ledger)
        return ledger

    def list(self) -> List[ResearchLedger]:
        with self._write_lock:
            ledgers: List[ResearchLedger] = []
            for path in sorted(self.storage_dir.glob("*.json")):
                with path.open("r", encoding="utf-8") as handle:
                    ledgers.append(ResearchLedger.model_validate(json.load(handle)))
            return ledgers

    def find_by_run_id(self, run_id: str) -> Optional[ResearchLedger]:
        with self._write_lock:
            for ledger in self.list():
                if ledger.run_id == run_id:
                    return ledger
                if ledger.ledger_id == run_id:
                    return ledger
                if any(entry.task_id == run_id for entry in ledger.task_history):
                    return ledger
            return None

    def get_storage_path(self, ledger_id: str) -> Path:
        safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", ledger_id)
        return self.storage_dir / f"{safe_name}.json"

    def _write(self, path: Path, ledger: ResearchLedger) -> None:
        payload = ledger.model_dump(mode="json", exclude_none=True)
        temp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        last_error: OSError | None = None
        for _ in range(5):
            try:
                os.replace(temp_path, path)
                return
            except OSError as exc:
                last_error = exc
                time.sleep(0.02)
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)
        if last_error is not None:
            raise last_error
