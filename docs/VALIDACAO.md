# Validação — FlyWorld 1.0

Data: 22/10/2026. Windows, Python 3.12.10, ambiente `.venv` local, sem CUDA.
Base upstream: `a3db62f9436074e485c0278290c2164ed6150808`.

## Inspeção original

Foram examinados README.md, main.py, code/benchmark.py, code/run_brian2_cuda.py, code/run_pytorch.py, code/paper-phil-drosophila/model.py e ambos os arquivos de dados solicitados.

- `benchmark.EXPERIMENTS`: 21 sugar GRNs a 200 Hz; dois P9 a 100 Hz. IDs usados diretamente via leitura AST; todos encontrados no CSV de completude.
- Brian2: `create_network`/`create_model` constroem neurônios LIF, sinapses ponderadas e SpikeMonitor. `add_poisson_inputs`/`poi` injetam tensão estocástica; `Network.run` executa; `spike_trains` fornece tempos por neurônio.
- O runner CPU original usa standalone C++ para um trial e joblib/runtime para múltiplos trials; cada trial é independente. O wrapper original não é uma interface persistente de ambiente.
- PyTorch: `get_hash_tables`, `get_weights`, `TorchModel.state_init` e `TorchModel.forward` constroem/mantêm tensores; estados são passados entre passos de 0,1 ms; a máscara de spikes fornece registros. CUDA é opcional nessa implementação original. FlyWorld não importa PyTorch.
- CSV: 138.639 IDs. Parquet: 15.091.983 linhas, índices pré/pós inteiros e pesos `Excitatory x Connectivity`. Peso efetivo Brian2 = coluna × 0,275 mV. Dados e scripts originais não foram modificados.
- Reset original inclui `w = 0`, mas `w` só está declarado em Synapses. Adaptador remove essa atribuição inválida apenas na cópia local dos parâmetros.

## Evidências executadas

1. Suíte `python -m pytest tests -q`: 15 testes aprovados após implementação e correções. Testes de worker usam spawn real no Windows e verificam encerramento, inclusive em erro.
2. Rede completa: setup inicial de 3,26 s; blocos 0–20 e 20–40 ms de 3,28 e 3,09 s, preservando relógio. Execuções posteriores aquecidas ficaram mais rápidas; não representam benchmark formal.
3. Ensaio P9 independente, semente 42, 200 ms, 100 Hz: 114 spikes totais, 35 nos P9; média P9 87,5 Hz. Processamento total 17,77 s, setup 1,25 s.
4. Baseline independente P9, semente 42, 200 ms, intensidade zero: zero spikes. Processamento 22,20 s, setup 1,81 s. A ausência de atividade espontânea é um resultado desta condição/modelo, não uma afirmação sobre cérebro biológico.
5. Açúcar, 21 alvos a 200 Hz, 100 ms: 1.523 spikes totais, processamento 8,32 s e setup 1,28 s. Não houve spikes P9 nessa janela; o decoder não transforma atividade sugar arbitrária em aproximação.
6. Aplicativo live completo, 480 quadros headless: consumiu blocos até 60 ms, produziu movimento virtual pelo decoder e encerrou sem erro. Último bloco levou 2,20 s, fator de tempo real 0,0091x. Captura `live.png` inspecionada.
7. Replay completo de `p9-on.parquet` com baseline: terminou em 200 ms sem reiniciar automaticamente e exportou os spikes. Captura `replay.png` inspecionada.
8. Demo headless, inicialização, atualização física e screenshot `demo.png` inspecionada. Teste por eventos Pygame cobre adicionar comida, criar/remover obstáculos, ajuda, manual e exportação sem spikes fabricados.
9. `python -m pip check`: nenhuma dependência quebrada. `compileall`: sem erro de sintaxe. CLI de ajuda executada.

Os Parquets reais e sidecars JSON estão em `flyworld-output/p9-on.parquet`, `p9-baseline.parquet` e `sugar-on.parquet` (diretório gerado e ignorado pelo Git). Capturas ficam na raiz para revisão.

## Limites da verificação

A validação gráfica automatizada usou SDL dummy e inspeção das capturas; não constitui teste manual de uma janela visível. A retenção de estado foi verificada também pelo potencial de membrana em conectoma pequeno e identidade do objeto Network; não foi feita comparação bit a bit com o benchmark standalone original. Os ensaios completos têm uma semente e janelas curtas, sem inferência estatística. A comparação do dashboard usa taxas P9 de gravações fornecidas ou condições sequenciais live; não valida o decoder motor.

Não foram executados benchmarks CUDA/PyTorch ou todos os tempos do benchmark original. Sem alterações nos scripts originais, sua interface foi preservada; o reset inconsistente upstream continua sendo uma limitação documentada. O replay carrega o arquivo inteiro em RAM e a exportação S é síncrona (pode pausar a UI em arquivos muito grandes); o processamento neural live é separado e nunca executa no renderizador.
