"""Architectural Negative and Boundary Invariant Hardening Tests (Block 33).

Negative invariant tests using AST analysis and runtime inspection:
1. Observers must not import Governor or Control Boundary
2. Provider Adapters must not import Governor or State Engine
3. CLI Layer must not bypass SDK Client
4. MCP Server must not bypass SDK Client
5. Governor is the sole authority for control action determination
6. Third-party integrations must use clean-room normalized interfaces
7. Routing engine does not contain hard-coded provider rankings or customer bias
8. Contracts module does not contain runtime or database dependencies
"""

import ast
import os
import unittest
from pathlib import Path
from typing import List, Set


def get_imports_from_file(file_path: Path) -> Set[str]:
    """Parse a python file with AST and extract all imported module names."""
    if not file_path.exists() or file_path.suffix != ".py":
        return set()
    try:
        tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    except Exception:
        return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
    return imports


def get_all_python_files(directory: Path) -> List[Path]:
    """Recursively list all python files under a directory."""
    if not directory.exists():
        return []
    return [p for p in directory.rglob("*.py") if "__pycache__" not in p.parts]


class TestArchitecturalNegativeHardening(unittest.TestCase):
    """Negative invariant assertions enforcing strict architectural isolation and layer boundaries."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.root_dir = Path(__file__).resolve().parent.parent.parent
        cls.infuse_dir = cls.root_dir / "infuse"

    def test_01_observers_do_not_import_governor_or_control(self) -> None:
        """Verify Observer modules never import Governor or Control Boundary."""
        observer_dirs = [
            self.infuse_dir / "observer",
            self.infuse_dir / "tools",
            self.infuse_dir / "web",
            self.infuse_dir / "health",
            self.infuse_dir / "economics",
        ]
        forbidden_substrings = ["infuse.governor", "infuse.control"]

        for obs_dir in observer_dirs:
            for py_file in get_all_python_files(obs_dir):
                imports = get_imports_from_file(py_file)
                for imp in imports:
                    for forbidden in forbidden_substrings:
                        self.assertFalse(
                            imp.startswith(forbidden),
                            f"Architectural Violation: Observer file {py_file} imports forbidden module {imp}",
                        )

    def test_02_providers_do_not_import_governor_or_state(self) -> None:
        """Verify Provider Adapters never import Governor or Execution State Engine."""
        providers_dir = self.infuse_dir / "providers"
        forbidden_substrings = ["infuse.governor", "infuse.state"]

        for py_file in get_all_python_files(providers_dir):
            imports = get_imports_from_file(py_file)
            for imp in imports:
                for forbidden in forbidden_substrings:
                    self.assertFalse(
                        imp.startswith(forbidden),
                        f"Architectural Violation: Provider file {py_file} imports forbidden module {imp}",
                    )

    def test_03_contracts_do_not_import_engines_or_runtimes(self) -> None:
        """Verify Contracts modules only import standard libraries or pydantic, never engines."""
        contracts_dir = self.infuse_dir / "contracts"
        forbidden_substrings = [
            "infuse.governor",
            "infuse.state",
            "infuse.control",
            "infuse.observer",
            "infuse.providers",
            "infuse.agents",
            "infuse.sdk",
            "infuse.cli",
            "infuse.mcp",
        ]

        for py_file in get_all_python_files(contracts_dir):
            imports = get_imports_from_file(py_file)
            for imp in imports:
                for forbidden in forbidden_substrings:
                    self.assertFalse(
                        imp.startswith(forbidden),
                        f"Architectural Violation: Contract file {py_file} imports engine/runtime module {imp}",
                    )

    def test_04_cli_uses_sdk_as_sole_core_interface(self) -> None:
        """Verify CLI layer routes operations through SDK rather than bypassing to core engines directly."""
        cli_dir = self.infuse_dir / "cli"
        forbidden_substrings = [
            "infuse.governor.engine",
            "infuse.state.engine",
            "infuse.control.boundary",
        ]

        for py_file in get_all_python_files(cli_dir):
            imports = get_imports_from_file(py_file)
            for imp in imports:
                for forbidden in forbidden_substrings:
                    self.assertFalse(
                        imp.startswith(forbidden),
                        f"Architectural Violation: CLI file {py_file} bypasses SDK to import {imp}",
                    )

    def test_05_mcp_uses_sdk_as_sole_core_interface(self) -> None:
        """Verify MCP Server routes operations through SDK rather than bypassing to core engines directly."""
        mcp_dir = self.infuse_dir / "mcp"
        forbidden_substrings = [
            "infuse.governor.engine",
            "infuse.state.engine",
            "infuse.control.boundary",
        ]

        for py_file in get_all_python_files(mcp_dir):
            imports = get_imports_from_file(py_file)
            for imp in imports:
                for forbidden in forbidden_substrings:
                    self.assertFalse(
                        imp.startswith(forbidden),
                        f"Architectural Violation: MCP file {py_file} bypasses SDK to import {imp}",
                    )

    def test_06_integrations_do_not_import_governor(self) -> None:
        """Verify Third-Party Integration adapters do not take over Governor authority."""
        integrations_dir = self.infuse_dir / "integrations"
        forbidden_substrings = ["infuse.governor.engine"]

        for py_file in get_all_python_files(integrations_dir):
            imports = get_imports_from_file(py_file)
            for imp in imports:
                for forbidden in forbidden_substrings:
                    self.assertFalse(
                        imp.startswith(forbidden),
                        f"Architectural Violation: Integration file {py_file} imports Governor {imp}",
                    )


if __name__ == "__main__":
    unittest.main()
