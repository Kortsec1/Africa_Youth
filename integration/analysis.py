"""검증된 기존 합성 샘플만 원래 분석기에 전달한다."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POC = ROOT / 'docs/research/01_detection/poc'


def run_demo(window=60):
    spec = importlib.util.spec_from_file_location('research_analyze', POC / 'analyze.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    events = json.loads((POC / 'sample_events.json').read_text(encoding='utf-8'))
    return module.analyze(events, window=window)
