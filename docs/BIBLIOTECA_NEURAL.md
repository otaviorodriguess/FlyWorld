# Integração do pacote nature_2026_07

O pacote do usuário foi registrado no FlyWorld como uma **biblioteca de gravações reais do modelo fly-brain**. O ZIP original permanece em Downloads e não foi alterado. Não foi necessário extrair seus 20,3 GB: o aplicativo consulta o manifesto e copia apenas os Parquets selecionados para um cache do projeto.

## O que foi aproveitado e implementado

1. **600 gravações indexadas**: experimento sugar, seis backends, cinco rodadas, durações 0,1/1/10/100 s e arquivos com 1/4/8/16/32 trials.
2. **Catálogo dentro do aplicativo** com filtro de backend, durações curtas/todas, arquivos de um trial/todos, paginação e seleção do trial individual.
3. **Importação seletiva, em segundo plano**, com CRC na leitura ZIP e SHA-256 comparado ao checksums.sha256 do pacote. Não há execução de código do ZIP nem extractall. Caminhos absolutos Linux no manifesto servem apenas para identificar o basename validado; não são usados como destino local.
4. **Replay no jardim 3D**, com duração exata do manifesto e redução da velocidade para observação. Um trial é filtrado na leitura Parquet quando a contagem de trials é conhecida. Os registros não são somados como se fossem uma única tentativa.
5. **Raster neural** dos 16 neurônios mais ativos: amostra visual determinística de até 5.000 spikes, com cursor do tempo de replay. Todos os dados continuam disponíveis para métricas/exportação, mesmo quando o raster reduz os pontos desenhados. Os IDs na tela são abreviados; os IDs completos estão nos Parquets. O raster mostra o arquivo completo, inclusive a parte ainda não reproduzida; o cursor marca a reprodução atual.
6. **Métricas dos grupos identificados**: contagem de spikes nos 21 sugar GRNs e nos dois P9 originais, sem inventar novos IDs. O painel distingue estímulo gravado de sliders atuais.
7. **Comparação com Brian2 CPU** na mesma duração, rodada, número de trials no arquivo e trial selecionado. Inclui contagem de spikes, neurônios ativos, média populacional, Jaccard dos conjuntos ativos, correlação de taxas por neurônio e correlação da contagem populacional em 50 bins. O JSON é exportado no cache.
8. **Proveniência na sessão**: arquivo selecionado, trial, duração e SHA-256 são registrados junto à telemetria. O cache tem sidecars JSON.

## Abrir e usar

Abra `biblioteca-neural.cmd` ou pressione **O** / clique em **Biblioteca neural** no topo do FlyWorld. O caminho do ZIP fica em `flyworld-output/archive-settings.json` depois do registro.

- **Tab**: alternar filtro de backend.
- **L**: durações até 1 s / todas.
- **N**, dentro da biblioteca: arquivos de um trial / todos.
- **Setas cima/baixo**, roda ou PageUp/PageDown: navegar.
- **Setas esquerda/direita** ou botões Trial: escolher trial, numerado a partir de zero.
- **Enter / Reproduzir**: importar a seleção e abrir replay no jardim.
- **F8 / Comparar 6 backends**: comparar a condição selecionada e mostrar o relatório.
- **Esc / O**: fechar biblioteca. A simulação fica suspensa enquanto o catálogo está aberto; não é preciso alterar a pausa manual.
- **N**, fora da biblioteca: mostrar/ocultar raster neural.
- **R**: repetir o replay atual. **- / =**: ajustar velocidade; a interface aceita até 0,01x para observação.

O replay escolhido pelo catálogo inicia a até 0,1x para ser observável. Ele termina e pausa ao chegar ao fim, sem inventar uma continuação da atividade. As interações guiadas do demo são encerradas ao carregar uma gravação; o controle manual pode ser ativado com M.

### Linha de comando

```powershell
.\.venv\Scripts\python -m flyworld --archive "C:\Users\Administrador\Downloads\nature_2026_07.zip" --library

.\.venv\Scripts\python -m flyworld --recording round_01/brian2cpp_t1.0s_n1.parquet --replay-speed 0.1

.\.venv\Scripts\python -m flyworld.recordings --archive "C:\Users\Administrador\Downloads\nature_2026_07.zip" --compare --duration 1 --trials 1 --round 1 --trial 0 --report docs/NEURAL_ARCHIVE_REPORT.json
```

Se mover o ZIP, registre novamente com `--archive novo/caminho.zip`. As gravações selecionadas ficam em `flyworld-output/recordings-cache/<identidade>/round_XX/`. O limite padrão é **64 MiB de tamanho do Parquet por importação**, ajustável com `--max-recording-mb`. O tamanho em RAM pode ser maior que o arquivo comprimido. Arquivos grandes continuam visíveis no catálogo, mas são recusados quando excedem esse limite; não foram importados todos os 600 arquivos.

A importação/comparação ocorre em uma thread de trabalho; a renderização continua e há encerramento cooperativo. A comparação processa as fontes sucessivamente, sem guardar todas as seis tabelas simultaneamente. Uma cópia em cache é novamente verificada antes de reutilização.

## Resultado real da análise

Condição: sugar 200 Hz, rodada 1, 1 s, arquivo de um trial, trial 0; população local de 138.639 neurônios.

| Backend | Spikes | Ativos | Jaccard com CPU | Correlação de taxas com CPU |
|---|---:|---:|---:|---:|
| Brian2 CPU | 16.567 | 380 | 1,0000 | 1,0000 |
| Brian2 CUDA | 16.418 | 405 | 0,8916 | 0,9930 |
| PyTorch | 17.429 | 415 | 0,8929 | 0,9913 |
| NEST GPU | 17.233 | 412 | 0,8993 | 0,9935 |
| GeNN | 16.978 | 386 | 0,9343 | 0,9896 |
| Brian2GeNN | 16.738 | 383 | 0,9365 | 0,9905 |

Os seis SHA-256 dessa condição foram conferidos. O relatório completo está em `NEURAL_ARCHIVE_REPORT.json`. Isso verifica os arquivos utilizados, não a integridade de todos os 20,3 GB.

As correlações das taxas por neurônio são altas, mas as correlações da contagem populacional em bins são bem menores (aproximadamente 0,11–0,29 contra CPU nos demais backends). Taxas semelhantes não significam os mesmos spikes nos mesmos instantes, nem garantem equivalência do motor. Essas métricas são descritivas, em uma condição e rodada; não houve validação estatística completa das 600 gravações.

No replay Brian2 CPU analisado, 4.127 spikes vieram dos sugar GRNs e **zero dos P9**. A mosca pode ficar parada: não foi criada uma regra para converter qualquer spike de açúcar em caminhada. O manual continua disponível e permanece identificado como tal.

## O que o pacote não permite afirmar

Ele não acrescenta um novo conectoma, treinamento comportamental, voo, aprendizagem ou respostas ao carinho. Todas as 600 linhas do manifesto identificam sugar; não há ensaio P9 nem baseline sem estímulo neste pacote. Não é correto comparar esses arquivos como se fossem condições com/sem açúcar, ou usar suas diferenças como prova de aprendizagem.

O replay não reage à comida adicionada agora; a resposta ao ambiente depende do modo live, que continua usando a rede persistente Brian2 existente. Comparar gravações não exige instalar CUDA, PyTorch, GeNN ou NEST GPU: os spikes desses backends já estão armazenados.

## Compatibilidade temporal e testes

Alguns arquivos, incluindo NEST GPU, têm spikes exatamente no instante final declarado (1.000 ms em um ensaio de 1 s). O replay foi ajustado para aceitar esse evento: janelas internas são `[início,fim)` e a última inclui o endpoint final. Isso evita descartar um spike legítimo ou inventar duração extra.

Os testes usam pequenos ZIPs técnicos gerados em fixtures, sem depender do pacote de 20 GB: catálogo, seleção, isolamento de trials, endpoint final, cache, SHA-256 divergente, limite de importação, rejeição de caminhos inadequados, comparação e ciclo de vida assíncrono. Também foi verificado o fluxo completo no aplicativo com o ZIP real: catálogo → comparar → carregar → raster no jardim.
