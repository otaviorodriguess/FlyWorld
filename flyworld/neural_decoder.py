"""Experimental P9 rate decoder; not a validated motor circuit model."""
from .experiments import get_experiment
from .fly_body import MotorCommand

class NeuralDecoder:
    def __init__(self, reference_hz: float = 100, gain: float = 1):
        if reference_hz <= 0 or gain < 0:
            raise ValueError('Referência deve ser positiva e ganho não negativo.')
        self.reference_hz, self.gain = reference_hz, gain
        self.ids = get_experiment('p9')['neu_exc']

    def decode(self, spikes, window_ms: float) -> MotorCommand:
        if window_ms <= 0 or spikes.empty:
            return MotorCommand()
        count = spikes.flywire_id.isin(self.ids).sum()
        rate = count / len(self.ids) / (window_ms / 1000)
        return MotorCommand(forward_drive=min(1., self.gain * rate / self.reference_hz))
