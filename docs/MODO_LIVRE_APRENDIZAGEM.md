# Modo Livre: autonomia, memória e aprendizagem

O modo padrão agora é `autonomous` (Livre). A mosca explora sem comandos manuais, busca comida observada, guarda memória entre execuções e atualiza uma política artificial por experiência. O cérebro completo Brian2 CPU executa em processo separado, como observador dos estímulos sensoriais. A biblioteca das 600 gravações continua acessível com O.

```powershell
.\.venv\Scripts\python -m flyworld
.\.venv\Scripts\python -m flyworld --mode autonomous
# Opcional: desligar apenas o observador neural, mantendo a autonomia
.\.venv\Scripts\python -m flyworld --mode autonomous --no-neural-observer
```

## O que aprende

`learning.py` implementa Q-learning tabular real: os valores das ações mudam com recompensas e penalidades. O estado discretiza a direção/distância do objetivo, proximidade frontal/lateral e presença de comida lembrada. As ações incluem avançar, curvar, girar, avançar devagar e parar. As decisões duram cerca de 0,35 s; a física continua com passo fixo.

Recompensas artificiais: comida coletada (+15), entrada em uma região ainda não visitada (+1,2), aproximação do objetivo (proporcional ao progresso), colisão (-2 por decisão) e custos pequenos de repetição/tempo/intervenção da proteção geométrica. Alpha=0,18 e gamma=0,92. A exploração aleatória começa em 28% e decai até 5% conforme as atualizações da tabela. Esses números são decisões de engenharia, não parâmetros biológicos da mosca.

A memória espacial registra regiões visitadas e alimentos vistos dentro do alcance dos sensores. Não consulta coordenadas ocultas de `world.foods` para escolher destinos. A seleção de um objetivo pouco visitado e a prevenção geométrica de colisões são auxiliares heurísticos; o Q-learning escolhe os comandos motores para chegar ao objetivo. Isso não é aprendizagem integral de percepção/locomoção a partir de pixels.

O estado e a política são salvos em `flyworld-output/learning/memory.json`, a cada 10 segundos de simulação e ao sair. O arquivo usa JSON e nunca executa código. R reinicia a arena, mas preserva os valores aprendidos. `--memory outro/arquivo.json` cria uma memória independente; não há remoção automática da memória existente.

## Separação do cérebro original

- **Cérebro simulado:** usa os 138.639 neurônios e toda a conectividade local original, com estado preservado entre blocos. O ambiente envia intensidade sugar/P9, e o worker devolve spikes reais do modelo.
- **Agente aprendiz:** controla o corpo no modo Livre por Q-learning e memória espacial. Os spikes não são fabricados para representar aprendizagem.
- **Conectoma original:** seus pesos não são alterados pelo Q-learning. Não foi adicionada uma regra de plasticidade biológica validada ao modelo LIF.

Portanto, a capacidade nova é **aprendizagem artificial de uma política de comportamento**, não evidência de que o cérebro da mosca aprendeu, tem sentimentos ou consciência. Não se afirma que os dados Parquet treinem a mosca a buscar comida. As gravações continuam úteis para replay/análise; o modo Livre não mistura spikes de arquivos com os spikes do observador Brian2.

O CPU não acompanha o mundo em tempo real. No modo Livre, a física e o agente seguem seu próprio relógio; a rede recebe uma amostra sensorial por solicitação e pode devolvê-la segundos depois. O painel mostra relógio neural, fator de tempo real e o instante do mundo em que o estímulo foi amostrado. Essa execução é uma observação assíncrona, não um circuito sensoriomotor neural fechado em tempo real. No modo 3/live, o comportamento continua usando apenas o decoder neural experimental anterior, sem Q-learning.

Se o observador falhar, a autonomia artificial continua e o erro neural aparece no painel. Não se substituem resultados ausentes por spikes sintéticos.

## Controles e observabilidade

- **4:** modo Livre; **1:** demo; **2:** replay; **3:** live com decoder experimental.
- **U:** pausar/retomar as atualizações Q. A política aprendida continua disponível, e a memória espacial mantém observações; não são criadas novas experiências Q enquanto pausado.
- **M:** controle manual. Movimentos manuais não são usados como transições Q.
- **B/K/J/L e botões:** alimentar/carinho/brincar/liberar exploração. A aprendizagem é suspensa durante interações guiadas; seus movimentos não recebem crédito de aprendizagem autônoma.
- **O:** biblioteca neural; **S:** exportação; **H:** ajuda.

O painel mostra atualizações Q, estados aprendidos, comidas coletadas na sessão, células visitadas, alimentos lembrados, ação atual, recompensa e taxa de exploração. A trilha do minimapa representa memória espacial, não atividade neural. O painel neural mostra contagens reais por bloco e a média populacional. A antiga frase ambígua “Dados neurais: nenhum” foi substituída, no demo, por uma indicação de que o cérebro está disponível e inativo naquele modo.

A telemetria registra controlador, contagem de atualizações, recompensa, instante de amostragem sensorial e relógio neural. Os spikes de um bloco são gravados uma única vez, mesmo quando a física avança mais rápido que o cérebro.

## Evidência medida

Foi executado um currículo técnico com comida próxima em uma arena pequena, sem obstáculos, usando o mesmo corpo e código de colisões. O modelo inicial foi comparado ao treinado no mesmo conjunto de avaliação (semente 2026), separado do conjunto usado no treino (semente 42):

| Condição | Alimentos encontrados / tentativas |
|---|---:|
| Agente inicial, sem treino | 5 / 40 |
| Após treino de 120 episódios | 40 / 40 |

O treino produziu 1.648 atualizações Q e 47 estados na tabela. `docs/LEARNING_EVALUATION.json` contém o resultado original. O checkpoint foi disponibilizado ao agente, que continua aprendendo durante o uso. Não é uma avaliação estatística de generalização nem prova de melhoria em todo o jardim, com lagos e obstáculos. A memória do mapa do currículo foi limpa antes de iniciar o jardim, para não confundir regiões de ambientes diferentes.

No teste integrado com a rede completa, o mundo avançou aproximadamente 17,25 s, o cérebro avançou 100 ms e produziu 676 spikes reais. O agente realizou 49 novas atualizações Q e coletou duas frutas. Foram conferidos os instantes de amostragem e a exportação dos spikes. A diferença de relógios foi mantida visível; esse ensaio não mede causalidade neural sobre as ações do agente.

Para repetir o currículo sem sobrescrever sua memória principal:

```powershell
.\.venv\Scripts\python -m flyworld.learning --memory flyworld-output/learning/experimento.json --episodes 120 --report flyworld-output/learning/experimento-report.json
```

## Limitações

A tabela usa uma representação pequena, não aprendizagem profunda. Objetivos geométricos e proteção contra colisões continuam heurísticos. O agente pode revisitar locais, ficar preso em configurações difíceis e não encontrar uma rota global em volta de lagos. A aprendizagem melhora tarefas medidas, não garante melhora monotônica nem autonomia biológica. Não há necessidades metabólicas, voo aprendido, STDP ou atualização dos milhões de pesos sinápticos originais.

A suíte cobre mudanças de valores por recompensa, persistência, alimentos observados versus ocultos, pausa de aprendizagem, ganho no currículo, integração autônoma, suspensão durante interação e observação neural assíncrona sem avançar a física duas vezes ou duplicar spikes. Os testes não exigem CUDA.
