"""Persistent Brian2 CPU runtime, reusing the upstream network constructor."""
import importlib.util
import sys
from time import perf_counter
from pathlib import Path
import numpy as np
import pandas as pd
from .config import ROOT
from .experiments import get_experiment
from .brain_adapter import NeuralFrame, COLUMNS

class BrianRuntime:
    def __init__(self, experiment: str, comp_path: str | Path, con_path: str | Path, seed_value=42):
        from brian2 import prefs, set_device, seed, ms, Network, PoissonGroup, Synapses
        start = perf_counter()
        set_device('runtime')
        prefs.codegen.target = 'numpy'  # no C++ compiler or CUDA required
        seed(seed_value)
        code_path = str(ROOT/'code')
        if code_path not in sys.path:
            sys.path.insert(0, code_path)
        spec = importlib.util.spec_from_file_location('flyworld_upstream_brian', ROOT/'code/run_brian2_cuda.py')
        upstream = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(upstream)
        params = dict(upstream.default_params)
        # Upstream reset writes w, although w exists only on Synapses. Remove
        # that undefined neuron assignment locally; v/g resets stay identical.
        params['eq_rst'] = 'v = v_rst; g = 0 * mV'
        neu, syn, monitor, comp, _ = upstream.create_network(comp_path, con_path, params)
        self.ids = comp.index.to_numpy(dtype=np.int64)
        self.population = len(comp)
        self.experiment = get_experiment(experiment)
        mapping = {int(n): i for i, n in enumerate(self.ids)}
        indices = [mapping[n] for n in self.experiment['neu_exc']]
        neu.rfc[indices] = 0*ms
        # Independent Poisson source per stimulated neuron, injecting the same
        # voltage weight and synapses scheduling slot as upstream PoissonInput.
        self.source = PoissonGroup(len(indices), rates=0*upstream.Hz)
        injection = Synapses(self.source, neu, on_pre='v_post += weight',
                             namespace={'weight': params['w_syn']*params['f_poi']})
        injection.connect(i=np.arange(len(indices)), j=indices)
        injection.pre.when = 'synapses'
        self.net = Network(neu, syn, self.source, injection, monitor)
        self.monitor = monitor
        self.Hz, self.ms = upstream.Hz, ms
        self.offset = 0
        self.setup_s = perf_counter()-start

    def advance(self, block_ms: float, intensity: float) -> NeuralFrame:
        from brian2 import SpikeMonitor
        if not np.isfinite(block_ms) or block_ms <= 0:
            raise ValueError('Bloco neural inválido.')
        # Replace only recording buffers. The neural state and delayed events
        # remain in the same Network across all blocks.
        self.source.rates = float(np.clip(intensity, 0, 1))*self.experiment['stim_rate']*self.Hz
        start_ms = float(self.net.t/self.ms)
        start = perf_counter()
        self.net.run(block_ms*self.ms, namespace={})
        idx = np.asarray(self.monitor.i, dtype=np.int64)
        ts = np.asarray(self.monitor.t/self.ms, dtype=float)
        data = pd.DataFrame({'time_ms': ts, 'trial': np.zeros(len(idx), dtype=np.int64),
            'neuron_index': idx, 'flywire_id': self.ids[idx], 'exp_name': self.experiment['key']})
        frame = NeuralFrame(start_ms, float(self.net.t/self.ms), data[COLUMNS],
                            perf_counter()-start, self.population, self.experiment['key'], intensity)
        self.net.remove(self.monitor)
        self.monitor = SpikeMonitor(self.net['default_neurons'])
        self.net.add(self.monitor)
        return frame
