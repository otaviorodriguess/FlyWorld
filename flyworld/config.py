from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Config:
    width: int = 6000
    height: int = 4000
    dt: float = 1 / 120
    sensor_range: float = 220
    max_speed: float = 110
    max_turn: float = 2.8
    neural_block_ms: float = 20

    def __post_init__(self):
        if not 0 < self.dt <= 0.1:
            raise ValueError('O passo físico deve estar entre 0 e 0,1 segundo.')
        if self.neural_block_ms <= 0:
            raise ValueError('O bloco neural deve ser positivo.')
