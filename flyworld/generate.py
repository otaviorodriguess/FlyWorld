"""Generate real CPU neural recordings without requiring a C++ compiler."""
import argparse
import json
from pathlib import Path
import pandas as pd
from .config import ROOT
from .brain_adapter import empty_spikes
from .__main__ import positive

def main():
    parser = argparse.ArgumentParser(description='Gerar spikes reais Brian2 CPU para replay FlyWorld')
    parser.add_argument('--experiment',choices=['p9','sugar'],default='p9')
    parser.add_argument('--duration-ms',type=positive,default=200)
    parser.add_argument('--block-ms',type=positive,default=20)
    parser.add_argument('--intensity',type=float,default=1)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if not 0<=args.intensity<=1:
        parser.error('--intensity deve estar entre 0 e 1')
    if args.output.exists():
        parser.error('O arquivo de saída já existe; escolha outro nome.')
    from .live_backend import BrianRuntime
    brain = BrianRuntime(args.experiment,ROOT/'data/2025_Completeness_783.csv',ROOT/'data/2025_Connectivity_783.parquet',args.seed)
    print(f'Rede completa: {brain.population} neurônios, setup {brain.setup_s:.2f}s',flush=True)
    frames = []
    elapsed, processing = 0.,0.
    while elapsed < args.duration_ms-1e-8:
        frame = brain.advance(min(args.block_ms,args.duration_ms-elapsed),args.intensity)
        frames.append(frame.spikes)
        elapsed = frame.end_ms
        processing += frame.processing_s
        print(f'{elapsed:.1f} ms / {args.duration_ms} ms: {len(frame.spikes)} spikes, {frame.processing_s:.2f}s CPU',flush=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    data = pd.concat(frames,ignore_index=True) if frames else empty_spikes()
    data.to_parquet(args.output,index=False)
    args.output.with_suffix('.json').write_text(json.dumps({'source':'flyworld Brian2 CPU / upstream network',
        'experiment':args.experiment,'intensity':args.intensity,'duration_ms':args.duration_ms,
        'seed':args.seed,'population':brain.population,'processing_s':processing,'setup_s':brain.setup_s,
        'reset_correction':'undefined neuron w assignment removed'},indent=2),encoding='utf-8')
    print(f'Salvo: {args.output} ({len(data)} spikes)',flush=True)

if __name__=='__main__':
    main()
