# FlyWorld 1.0 — mundo 3D

**Modo padrão: Livre.** Execute `python -m flyworld` para exploração autônoma, Q-learning artificial e memória persistente, com o cérebro completo como observador assíncrono. **U** pausa a aprendizagem e **4** seleciona esse modo. Os pesos do conectoma não são modificados. Veja [autonomia, aprendizagem e resultados](docs/MODO_LIVRE_APRENDIZAGEM.md).

**Biblioteca neural integrada:** pressione **O** ou abra `biblioteca-neural.cmd` para selecionar gravações do ZIP `nature_2026_07`, verificar SHA-256, reproduzir no jardim e comparar backends. **N** alterna o raster neural fora do catálogo. Veja [uso e análise do pacote](docs/BIBLIOTECA_NEURAL.md).

O jardim agora tem **6.000 × 4.000 unidades (25× a área original)**, lagos, árvores, flores e um minimapa. Use os botões para **alimentar, chamar, fazer carinho, brincar com luz e explorar**. Veja [interações e navegação pelo jardim](docs/JARDIM_INTERACOES.md). As respostas lúdicas são heurísticas e não substituem o cérebro nos modos neurais.

A visualização padrão agora usa perspectiva 3D, câmera orbital e mosca detalhada com asas translúcidas e pernas animadas. Veja [controles e implementação 3D](docs/MUNDO_3D.md). Use **C** para visão geral, **roda** para zoom, **A/D** para girar e **V** para alternar 3D/2D. A locomoção continua no chão.

MVP em Python/Pygame para explorar um corpo virtual e observar spikes do fly-brain. Os arquivos originais estão preservados. A base é o repositório [eonsystemspbc/fly-brain](https://github.com/eonsystemspbc/fly-brain), commit `a3db62f9436074e485c0278290c2164ed6150808`, sob sua licença GPL-2.0.

## Instalação

Python 3.10+; validado neste ambiente com Python 3.12.10, Windows, sem GPU.

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-flyworld.txt
.\.venv\Scripts\python -m flyworld --mode demo
```

Em Linux/macOS use `.venv/bin/python`. A instalação requer acesso ao índice de pacotes; depois disso o aplicativo e o backend CPU funcionam localmente, sem APIs. O backend NumPy dispensa compilador C++. O ambiente virtual já foi preparado nesta entrega. No Windows, você também pode abrir `iniciar-flyworld.cmd` com duplo clique.

## Execução

```powershell
.\.venv\Scripts\python -m flyworld --mode demo
.\.venv\Scripts\python -m flyworld --mode replay --spikes flyworld-output/p9-on.parquet --baseline-spikes flyworld-output/p9-baseline.parquet
.\.venv\Scripts\python -m flyworld --mode live --backend brian2 --experiment p9
.\.venv\Scripts\python -m flyworld --mode live --experiment sugar
.\.venv\Scripts\python -m flyworld --help
```

`--dt` configura o passo físico em segundos (até 0,1); `--block-ms` configura blocos neurais/replay (padrão 20 ms). `--decoder-gain` altera o ganho experimental do movimento. `--trial` seleciona uma tentativa; `--replay-exp` seleciona exatamente o valor de `exp_name` quando o arquivo contém vários experimentos. O replay não mistura trials.

`--duration-ms` informa a duração conhecida, incluindo silêncio após o último spike. Na ausência desse argumento, arquivos gerados pelo FlyWorld usam o sidecar JSON; nos demais arquivos o final é inferido como último spike + 0,1 ms. Isso não permite inferir a duração real de um experimento silencioso. Para comparações quantitativas, forneça a duração real. A duração não pode preceder o último spike; o endpoint final é incluído quando existe um spike exatamente nele.

## Controles

| Controle | Ação |
|---|---|
| Espaço | Iniciar/pausar |
| R | Reiniciar arena, replay/rede e criar outra sessão de gravação |
| Clique esquerdo | Adicionar alimento verde |
| Clique direito | Criar/remover obstáculo no ponto clicado |
| 1 / 2 / 3 | Demo / replay / live; replay exige `--spikes` na inicialização |
| M e setas | Alternar manual; cima avança, esquerda/direita giram, baixo para |
| [ / ] | Ajustar ganho do estímulo entre 0 e 1 |
| T | Ligar/desligar estímulo neural |
| E | Alternar sugar/P9; live reconstrói a rede, replay permanece imutável |
| - / = | Velocidade de tempo entre 0,25x e 4x |
| G | Ocultar/mostrar gráficos |
| Roda do mouse | Zoom com câmera acompanhando a mosca |
| S | Exportar snapshot dos dados |
| H / Esc | Ajuda / sair |

No live sugar, aproxime alimento clicando perto da mosca: intensidade = ganho × proximidade geométrica, chegando a 200 Hz nos 21 receptores originais. No live P9 a estimulação é ganho × 100 Hz nos dois P9. T permite observar atividade com/sem estímulo. O dashboard mostra médias P9 e barras por condição observada. Essa comparação sequencial tem efeitos de estado residual; não é um ensaio controlado independente. Para ensaios independentes, use o gerador abaixo.

No replay os controles de estímulo não alteram os dados gravados. Obstáculos e movimento manual continuam sendo física virtual. A cor azul identifica dados neurais e o decoder experimental; âmbar identifica política heurística/sensores geométricos.

## Gerar spikes reais

O caminho original permanece disponível, conforme o README original e suas dependências:

```powershell
python main.py --brian2-cpu --experiment p9 --t_run 0.1 --n_run 1 --run-label flyworld_p9
python main.py --brian2-cpu --experiment sugar --t_run 0.1 --n_run 1 --run-label flyworld_sugar
```

O runner original usa C++ standalone quando `n_run=1`, exige compilador e possui uma inconsistência no reset (`w` atribuído ao neurônio, embora declarado apenas na sinapse). Esses benchmarks não foram alterados nem certificados pela suíte FlyWorld. Consulte o README original para o ambiente completo; dependências opcionais CUDA/PyTorch não são instaladas pelo FlyWorld. A coluna `spike_path` do manifesto identifica o Parquet exportado em `data/results/<label>/`.

Há também um gerador CPU runtime que usa a construção original da rede, com a correção local do reset aplicada somente ao adaptador:

```powershell
.\.venv\Scripts\python -m flyworld.generate --experiment p9 --duration-ms 200 --intensity 1 --output flyworld-output/p9-on.parquet
.\.venv\Scripts\python -m flyworld.generate --experiment p9 --duration-ms 200 --intensity 0 --output flyworld-output/p9-baseline.parquet
.\.venv\Scripts\python -m flyworld.generate --experiment sugar --duration-ms 100 --output flyworld-output/sugar-on.parquet
```

Cada execução cria uma rede independente, usa semente 42 por padrão (`--seed`) e grava JSON com duração, condição, população e tempos. O gerador recusa sobrescrever arquivos existentes. Seus dados são spikes reais do modelo, não dados sintéticos de demonstração. Execuções longas do gerador acumulam os frames em memória: prefira gravações curtas; o aplicativo registra em disco.

## Dados e métricas

Parquet: uma linha por spike, colunas `time_ms`, `trial`, `neuron_index`, `flywire_id`, `exp_name`. `t` legado é aceito como segundos quando `time_ms` está ausente. IDs precisam ser inteiros; não converta IDs FlyWire para float, que perde precisão. Tempos inválidos/negativos e arquivos ambíguos são rejeitados. Janelas internas de replay são `[início,fim)` (a última inclui o endpoint final) e usam busca binária, sem repetir ou perder spikes nas bordas.

Ativos e spikes referem-se ao bloco atual. A frequência média é `n_spikes / duração_s / população_total`; não é a média apenas entre neurônios ativos. A população é a do arquivo de completude local; para dados de outra rede essa métrica não é apropriada. O gráfico mostra contagem de spikes por bloco, não uma frequência biologicamente calibrada.

Cada sessão cria `flyworld-output/<timestamp>/metadata.json`, `telemetry.csv` e `spikes.csv`. S e encerramento normal exportam `spikes.parquet` em blocos para limitar memória. Reset/troca de modo fecha a sessão anterior, mantendo seus CSVs. O demo grava telemetria e um Parquet vazio: nunca inventa spikes. A telemetria registra posição, modo/controlador, sensores, estímulo efetivamente aplicado e métricas. No replay, estímulo aplicado é desconhecido; o valor não é inferido do slider. Eventos ambientais entre blocos não equivalem a estímulos cerebrais registrados.

## Arquitetura

- `world.py`: arena principal 6000 × 4000, alimentos, obstáculos e geometria de colisões.
- `fly_body.py`: estado físico e comandos abstratos; não importa backend neural.
- `sensors.py`: distância/proximidade e três raios geométricos.
- `controllers.py`: exploração/atração demo e prevenção de colisões, ambas heurísticas.
- `experiments.py`: lê por AST a tabela `EXPERIMENTS` original, sem importar GPU nem duplicar IDs.
- `brain_adapter.py`: frames neurais, replay validado e processo live com filas limitadas.
- `live_backend.py`: construtor original `create_network`, parâmetros LIF originais, Brian2 runtime/NumPy persistente.
- `neural_decoder.py`: taxa dos dois P9 para drive de avanço experimental.
- `app.py`: relógios, controles, física e ciclo de vida.
- `dashboard.py`: renderização e histórico limitado a 240 blocos.
- `recorder.py`: gravação em disco e exportação Parquet.
- `generate.py`: experimentos CPU curtos independentes para replay/comparação.

O worker carrega o conectoma uma vez por sessão live e mantém a mesma `Network`, potenciais, condutâncias, refratariedade e filas de eventos entre `net.run()` consecutivos. A fonte usa um PoissonGroup por alvo e sinapses de injeção de tensão no slot `synapses`, com peso `w_syn × f_poi`, reproduzindo a forma de entrada do PoissonInput original. Não se afirma identidade bit a bit dos geradores aleatórios. O SpikeMonitor é substituído após cada bloco para limitar a memória de gravação; o cérebro não é reconstruído. Fechar/trocar modo solicita encerramento e, se um bloco não terminar no prazo, termina o worker com espera limitada.

A renderização continua a 60 FPS enquanto o worker calcula. O mundo avança apenas quando chega um bloco neural, usando o comando desse bloco como aproximação temporal explícita. Não há sincronização biológica contínua nem garantia de tempo real. A pausa deixa no máximo um bloco em andamento: ele é consumido ao continuar. Modificar um estímulo durante um bloco passa a valer na próxima solicitação. Velocidade altera a cadência desejada, sem criar backlog ilimitado quando o CPU não acompanha.

## Fundamentação e limites científicos

A rede, IDs, pesos, parâmetros LIF e grupos sugar/P9 vêm do código original. Os dados locais inspecionados contêm **138.639 neurônios e 15.091.983 linhas de conectividade**; a quantidade de linhas difere da aproximação de 5 milhões no pedido/README original.

O decoder usa apenas os IDs P9 definidos no benchmark como associados à caminhada para frente. Calcula a taxa populacional P9 por bloco: `spikes_P9 / 2 / duração_s`, divide por 100 Hz e aplica ganho e saturação em `[0,1]`. Não interpreta qualquer spike arbitrário como ação. Ainda assim, é uma hipótese de controle virtual, sem calibração de velocidade, validação de causalidade motora ou modelo biomecânico. Blocos curtos têm taxas ruidosas e podem produzir movimento pulsado. Não há decoder validado para giro ou busca de alimento. Portanto sugar pode ativar o cérebro sem fazer a mosca aproximar-se: aproximação intencional só é demonstrada pelo controlador demo ou manual.

Não há olfato, aprendizagem, memória comportamental, decisão consciente ou circuito de desvio neural validado. Antenas/asas/pernas são ilustração. Sensores, arena, comida consumida, colisões e política de desvio são construções computacionais. Um resultado de movimento virtual não é evidência de comportamento natural da mosca.

## Desempenho e validação

O conectoma completo exige memória da ordem de gigabytes ao construir sinapses Brian2. Nesta máquina, um teste inicial de 20 ms neurais levou aproximadamente 3 segundos de processamento: live opera muito abaixo de tempo real. O fator exibido é duração neural / tempo de processamento do bloco, excluindo setup; o tempo de setup aparece separadamente. Replay usa o relógio da aplicação; seu tempo de processamento mede seleção de registros, não simulação cerebral.

```powershell
.\.venv\Scripts\python -m pytest tests -q
.\.venv\Scripts\python -m flyworld --mode demo --headless --frames 60 --screenshot demo.png
.\.venv\Scripts\python -m flyworld --mode replay --spikes flyworld-output/p9-on.parquet --headless --frames 30
.\.venv\Scripts\python -m pip check
```

A suíte cobre movimento, parada/giro, colisão sem atravessamento, sensores, coleta, decoder P9, Parquet/legado/validação, bordas temporais, trials, IDs originais, pausa/reset/exportação e ciclo de vida gráfico. Um conectoma pequeno verifica retenção de potenciais entre blocos, resposta com/sem estímulo e ciclo de vida do worker. Ele é uma fixture técnica; não representa o cérebro completo. Testes completos de desempenho foram executados separadamente com os dados reais e estão descritos em `docs/VALIDACAO.md`.

## Próximos passos

Validar/calibrar o decoder com dados de circuitos motores publicados; adicionar janelas de taxa suavizadas e experimentos replicados; comparar estatisticamente o runtime ao benchmark original após corrigir o reset upstream; otimizar CPU/codegen com medição; implementar streaming de Parquet muito grande (o replay atual carrega uma gravação em RAM). Substituir a política de obstáculos somente após validar um circuito. PyTorch/CUDA continuam opcionais no projeto original, sem integração live FlyWorld nesta versão.

## Versão web

Jardim 3D publicado em https://flyworld-garden.vercel.app. A versão web tem aprendizagem artificial salva no navegador e seis amostras de replay neural real. A execução completa Brian2 permanece no aplicativo local. Consulte docs/DEPLOY_VERCEL.md.
