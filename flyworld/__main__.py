"""Run with python -m flyworld --help."""
import argparse
import math
import os
import sys
from pathlib import Path
from .config import ROOT

def positive(value):
    number = float(value)
    if not math.isfinite(number) or number<=0:
        raise argparse.ArgumentTypeError('Use um número positivo e finito.')
    return number

def parser():
    p = argparse.ArgumentParser(description='FlyWorld 1.0 — arena virtual e atividade neural',
        epilog='H: ajuda na janela. Demo é heurístico; replay é gravação; decoder P9 é experimental.')
    p.add_argument('--view', choices=['3d','2d'], default='3d', help='Visualização (padrão: 3d)')
    p.add_argument('--mode', choices=['autonomous','demo','replay','live'], default='autonomous')
    p.add_argument('--memory',type=Path,default=ROOT/'flyworld-output/learning/memory.json',help='Memória persistente do agente artificial')
    p.add_argument('--no-learning',action='store_true',help='Congelar atualizações Q no modo Livre')
    p.add_argument('--no-neural-observer',action='store_true',help='Modo Livre sem executar Brian2 em paralelo')
    p.add_argument('--backend', choices=['brian2'], default='brian2')
    p.add_argument('--spikes', type=Path)
    p.add_argument('--archive', type=Path, help='ZIP de gravações; registra biblioteca para próximas execuções')
    p.add_argument('--library', action='store_true', help='Abrir o catálogo neural ao iniciar')
    p.add_argument('--recording', help='Membro relativo do ZIP, ex.: round_01/brian2cpp_t1.0s_n1.parquet')
    p.add_argument('--max-recording-mb', type=positive, default=64, help='Limite por Parquet importado, padrão 64 MiB')
    p.add_argument('--replay-speed', type=positive, default=1., help='Velocidade inicial do replay (ex.: 0.1)')
    p.add_argument('--trial', type=int, default=0)
    p.add_argument('--replay-exp', help='Valor exato da coluna exp_name')
    p.add_argument('--duration-ms', type=positive, help='Duração conhecida do replay; inclui silêncio final')
    p.add_argument('--baseline-spikes', type=Path, help='Gravação sem estímulo para comparação P9')
    p.add_argument('--experiment', choices=['sugar','p9'], default='sugar')
    p.add_argument('--dt', type=positive, default=1/120, help='Passo físico em segundos (máximo 0.1)')
    p.add_argument('--block-ms', type=positive, default=20, help='Bloco neural/replay em milissegundos')
    p.add_argument('--decoder-gain', type=positive, default=1., help='Ganho do decoder P9 experimental')
    p.add_argument('--output', type=Path, default=ROOT/'flyworld-output')
    p.add_argument('--headless', action='store_true', help='Driver SDL dummy para verificação automática')
    p.add_argument('--frames', type=int, default=0, help='Encerrar após N frames (0: sem limite)')
    p.add_argument('--screenshot', type=Path)
    return p

def main(argv=None):
    args = parser().parse_args(argv)
    if args.frames < 0:
        parser().error('--frames não pode ser negativo')
    if args.headless:
        os.environ['SDL_VIDEODRIVER']='dummy'
    os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
    try:
        from .app import App
        App(args).run()
    except (ValueError, OSError, ImportError) as exc:
        print(f'FlyWorld: {exc}', file=sys.stderr)
        print('Consulte python -m flyworld --help e requirements-flyworld.txt.', file=sys.stderr)
        return 2
    return 0

if __name__ == '__main__':
    import multiprocessing
    multiprocessing.freeze_support()
    raise SystemExit(main())
