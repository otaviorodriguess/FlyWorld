"""Read the upstream experiment table without importing optional GPU engines."""
import ast
from copy import deepcopy
from functools import lru_cache
from .config import ROOT

@lru_cache(maxsize=1)
def _definitions() -> dict:
    tree = ast.parse((ROOT / 'code/benchmark.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'EXPERIMENTS' for t in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError('Tabela EXPERIMENTS não encontrada no benchmark original.')

def get_experiment(name: str = 'sugar') -> dict:
    if name not in _definitions():
        raise ValueError(f'Experimento desconhecido: {name}')
    return deepcopy(_definitions()[name])
