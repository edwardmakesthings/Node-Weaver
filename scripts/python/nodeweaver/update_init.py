"""
Enhanced initialization file manager with configuration support.
Handles automatic updates of __init__.py files with configurable behavior.

Features:
- Custom import ordering rules
- Module dependency tracking
- Configurable docstrings
- Change detection
- Nested package support
"""

from pathlib import Path
import ast
import json
import logging
from typing import Dict, Set, List, Tuple, Optional
from dataclasses import dataclass
import importlib
import re
from enum import Enum

class ImportOrderPolicy(Enum):
    """Import ordering policies."""
    ALPHABETICAL = "alphabetical"
    CUSTOM = "custom"
    DEPENDENCY_FIRST = "dependency_first"
    LENGTH = "length"

@dataclass
class ModuleConfig:
    """Configuration for a module."""
    docstring: str
    order_policy: ImportOrderPolicy
    custom_order: Optional[List[str]] = None
    dependencies: Optional[List[str]] = None
    exports_blacklist: Optional[List[str]] = None

@dataclass
class ModuleInfo:
    """Information about a Python module."""
    classes: Dict[str, str]  # class name -> docstring
    functions: Dict[str, str]  # function name -> docstring
    imports: Set[str]
    exports: Set[str]
    dependencies: Set[str]

class ConfigurationManager:
    """Manages configuration for init file generation."""

    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.config: Dict[str, Dict] = self._load_config()

    def _load_config(self) -> Dict[str, Dict]:
        """Load configuration from JSON file."""
        if not self.config_path.exists():
            self._create_default_config()

        with self.config_path.open('r', encoding='utf-8') as f:
            return json.load(f)

    def _create_default_config(self) -> None:
        """Create default configuration file."""
        default_config = {
            "global": {
                "order_policy": "dependency_first",
                "docstring": "Auto-generated __init__.py file.",
                "exports_blacklist": ["internal_*", "test_*", "_*"]
            },
            "paths": {
                "core": {
                    "docstring": "Core components and base functionality.",
                    "order_policy": "dependency_first",
                    "custom_order": ["base", "interfaces", "utils"],
                    "dependencies": []
                }
            }
        }

        with self.config_path.open('w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=2)

    def get_module_config(self, module_path: Path) -> ModuleConfig:
        """Get configuration for a specific module."""
        # Convert path to config key
        rel_path = str(module_path.relative_to(self.config_path.parent))
        path_key = rel_path.replace('\\', '/').replace('/', '.')

        # Get most specific matching config
        config = None
        for key in self.config.get("paths", {}):
            if path_key.startswith(key):
                config = self.config["paths"][key]

        # Fallback to global config
        if not config:
            config = self.config["global"]

        return ModuleConfig(
            docstring=config.get("docstring", self.config["global"]["docstring"]),
            order_policy=ImportOrderPolicy(config.get("order_policy",
                                                    self.config["global"]["order_policy"])),
            custom_order=config.get("custom_order"),
            dependencies=config.get("dependencies", []),
            exports_blacklist=config.get("exports_blacklist",
                                       self.config["global"]["exports_blacklist"])
        )

class DependencyTracker:
    """Tracks module dependencies."""

    def __init__(self):
        self.dependencies: Dict[str, Set[str]] = {}

    def add_dependency(self, module: str, depends_on: str) -> None:
        """Add a dependency relationship."""
        if module not in self.dependencies:
            self.dependencies[module] = set()
        self.dependencies[module].add(depends_on)

    def get_ordered_modules(self, modules: Set[str]) -> List[str]:
        """Get modules ordered by dependencies."""
        visited = set()
        ordered = []

        def visit(module: str):
            if module in visited:
                return
            visited.add(module)
            for dep in self.dependencies.get(module, set()):
                if dep in modules:  # Only consider dependencies in our module set
                    visit(dep)
            ordered.append(module)

        for module in modules:
            visit(module)

        return ordered

class InitFileManager:
    """Manages automatic updates of __init__.py files."""

    def __init__(self, root_dir: Path, config_path: Optional[Path] = None):
        self.root_dir = root_dir
        self.logger = logging.getLogger(__name__)
        self.module_cache: Dict[str, ModuleInfo] = {}
        self.dependency_tracker = DependencyTracker()

        if config_path is None:
            config_path = root_dir / "init_config.json"
        self.config_manager = ConfigurationManager(config_path)

    def _analyze_imports(self, node: ast.AST) -> Set[str]:
        """Analyze imports in an AST node."""
        imports = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Import):
                for name in child.names:
                    imports.add(name.name)
            elif isinstance(child, ast.ImportFrom):
                if child.module:
                    imports.add(child.module)
        return imports

    def _should_export(self, name: str, blacklist: List[str]) -> bool:
        """Check if name should be exported based on blacklist patterns."""
        return not any(re.match(pattern, name) for pattern in blacklist)

    def _analyze_module(self, file_path: Path) -> ModuleInfo:
        """Analyze a Python module file."""
        if str(file_path) in self.module_cache:
            return self.module_cache[str(file_path)]

        with file_path.open('r', encoding='utf-8') as f:
            tree = ast.parse(f.read())

        classes = {}
        functions = {}
        imports = set()
        exports = set()
        dependencies = set()

        # Get module config
        config = self.config_manager.get_module_config(file_path)

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if self._should_export(node.name, config.exports_blacklist):
                    classes[node.name] = ast.get_docstring(node) or ''
                    exports.add(node.name)
            elif isinstance(node, ast.FunctionDef):
                if not node.name.startswith('_') and \
                   self._should_export(node.name, config.exports_blacklist):
                    functions[node.name] = ast.get_docstring(node) or ''
                    exports.add(node.name)

        # Analyze imports and dependencies
        imports = self._analyze_imports(tree)
        for imp in imports:
            if imp.startswith(str(self.root_dir.stem)):
                dependencies.add(imp)

        info = ModuleInfo(classes, functions, imports, exports, dependencies)
        self.module_cache[str(file_path)] = info

        # Track dependencies
        module_name = file_path.stem
        for dep in dependencies:
            self.dependency_tracker.add_dependency(module_name, dep)

        return info

    def _order_imports(self, imports: List[str], config: ModuleConfig) -> List[str]:
        """Order imports according to policy."""
        if config.order_policy == ImportOrderPolicy.CUSTOM and config.custom_order:
            # Sort based on custom order, putting unspecified at the end
            def get_sort_key(imp):
                try:
                    return config.custom_order.index(imp)
                except ValueError:
                    return len(config.custom_order)
            return sorted(imports, key=get_sort_key)

        elif config.order_policy == ImportOrderPolicy.DEPENDENCY_FIRST:
            # Use dependency tracker to order imports
            return self.dependency_tracker.get_ordered_modules(set(imports))

        elif config.order_policy == ImportOrderPolicy.LENGTH:
            return sorted(imports, key=len)

        else:  # ALPHABETICAL
            return sorted(imports)

    def generate_init_content(self, module_info: Dict[str, ModuleInfo],
                            config: ModuleConfig) -> str:
        """Generate content for __init__.py file."""
        imports = []
        exports = set()

        # Collect and organize imports
        for module_name, info in module_info.items():
            if info.exports:
                imports.append(f"from .{module_name} import {', '.join(sorted(info.exports))}")
                exports.update(info.exports)

        # Order imports according to policy
        ordered_imports = self._order_imports(imports, config)

        return f'''"""
{config.docstring}
"""

{chr(10).join(ordered_imports)}

__all__ = [
    "{('", "'.join(sorted(exports)))}"
]
'''

    def update_init_files(self) -> None:
        """Update all __init__.py files in the project."""
        for dir_path in self._find_package_dirs():
            try:
                # Get configuration for this directory
                config = self.config_manager.get_module_config(dir_path)

                # Scan and analyze modules
                module_info = {}
                for item in dir_path.iterdir():
                    if item.is_file() and item.suffix == '.py' and item.stem != '__init__':
                        module_info[item.stem] = self._analyze_module(item)

                # Generate and write content
                init_content = self.generate_init_content(module_info, config)
                init_file = dir_path / '__init__.py'

                # Only write if content has changed
                if not init_file.exists() or init_file.read_text() != init_content:
                    init_file.write_text(init_content)
                    self.logger.info(f"Updated {init_file}")

            except Exception as e:
                self.logger.error(f"Error updating {dir_path}: {e}")

    def _find_package_dirs(self) -> List[Path]:
        """Find all Python package directories in the project."""
        return [item.parent for item in self.root_dir.rglob('*/__init__.py')]

# Example usage
if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Update Python package __init__ files')
    parser.add_argument('root_dir', type=Path, help='Root directory of the Python package')
    parser.add_argument('--config', type=Path, help='Path to configuration file')

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    manager = InitFileManager(args.root_dir, args.config)
    manager.update_init_files()