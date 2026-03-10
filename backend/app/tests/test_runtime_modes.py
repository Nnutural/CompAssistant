import unittest
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.runtime_modes import resolve_runtime_mode


class RuntimeModeResolutionTests(unittest.TestCase):
    def test_mock_mode_is_supported(self) -> None:
        resolved = resolve_runtime_mode("mock")
        self.assertEqual(resolved.requested_runtime_mode, "mock")
        self.assertEqual(resolved.normalized_runtime_mode, "mock")

    def test_agents_sdk_mode_is_supported(self) -> None:
        resolved = resolve_runtime_mode("agents_sdk")
        self.assertEqual(resolved.requested_runtime_mode, "agents_sdk")
        self.assertEqual(resolved.normalized_runtime_mode, "agents_sdk")

    def test_live_alias_is_rejected_with_clear_message(self) -> None:
        with self.assertRaisesRegex(ValueError, "runtime_mode='live' is deprecated"):
            resolve_runtime_mode("live")


if __name__ == "__main__":
    unittest.main()
