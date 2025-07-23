import sys
from types import ModuleType
from pathlib import Path

# Stub kuzu to avoid heavy dependency during tests
sys.modules.setdefault('kuzu', ModuleType('kuzu'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from codebased.parsers.extractor import EntityExtractor
from codebased.config import CodeBasedConfig
from codebased.parsers.registry import PARSER_REGISTRY


class DummyDB:
    def execute_batch(self, queries):
        return True

    def clear_graph(self):
        return True


def test_extractor_initializes_all_parsers():
    cfg = CodeBasedConfig()
    extractor = EntityExtractor(cfg, DummyDB())
    assert set(extractor.parsers.keys()) == set(PARSER_REGISTRY.keys())
