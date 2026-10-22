# Jardim e lan house — Implementation Plan

> For agentic workers: use superpowers:executing-plans task by task. Execução nativa nesta sessão, conforme autorização do usuário.

**Goal:** Publicar o jardim reorganizado e uma lan house com Pong demonstrável, treinável e avaliável.
**Architecture:** Layout determinístico compartilhado; motor/agente/avaliação Pong puros; duas cenas no mesmo renderizador; integração UI isolada em um controlador da lan house.
**Tech Stack:** Three.js, JavaScript ESM, Vite, Node test, Playwright, Vercel.
**Spec:** ../specs/2026-10-22-jardim-lanhouse-pong-design.md

## Global Constraints
Mundo 6000 × 4000; seis estações com distância mínima 600; jogo de uma raquete contra parede, episódios de 30 segundos; recompensa +1 por devolução, -1 por perda. Avaliação de 100 episódios por política, sem explorar ou modificar pesos. Memória Pong independente e versionada; não alterar Brian2 ou replay. Um renderizador, um RAF; treino parado em aba oculta e no jardim.

## Review Focus
- Memória antiga: preservar Q e descobertas, invalidar coordenadas incompatíveis (tarefa 1).
- Colisão rápida: subpassos impedem atravessar a raquete (tarefa 2).
- Avaliação cancelada: sem resultados completos falsos ou mutação da política (tarefa 3).
- Teclas/touch ao trocar mapas: limpar entrada e pausar treino (tarefa 4).
- Falha de armazenamento: sessão continua e exportação permanece disponível (tarefa 4).

### Task 1 — Layout e mosca
Files: src/layout.js, layout.test.js, experiences.js, scenery.js, garden.js, fly-model.js, main.js.
Interfaces: createLayout() -> world com regions, paths, sites, spawn, portal; pathDistance(world,x,z); migrateGardenMemory(memory,version).
- [x] Testar seis estações seguras, separação >=600, rotas desde spawn e migração preservando Q.
- [x] Implementar layout com corredores livres, bosques e grupos de comida; física/render/mapa usam os mesmos caminhos.
- [x] Refinar postura e proporções; preservar seis pernas e duas asas.
- [x] Rodar npm test e commit.

### Task 2 — Pong e aprendizagem
Files: src/pong.js, pong.test.js.
Interfaces: Pong(seed).step(action,dt) -> eventos/reward/done; PongAgent(memory).act(game,{explore,rng}), demonstrate(state,action), update(...), snapshot().
- [x] Testar rebotes, perdas, limite 30s, demonstrações, Q updates e memória inválida.
- [x] Implementar passo fixo, três ações, estados discretizados sem previsão futura e preferência demonstrada apenas onde não há Q treinado.
- [x] Rodar npm test e commit.

### Task 3 — Avaliação reproduzível
Files: src/pong-evaluation.js, pong.test.js.
Interfaces: Evaluation(agent,100).advance(budget), cancel(), result.
- [x] Testar saques iguais, 100 episódios de cada política, cancelamento e checkpoint inalterado.
- [x] Implementar avaliação incremental, aleatória e política congelada; médias de devoluções/duração e conclusão explícita.
- [x] Medir política inicial e treinada, registrar resultados reais, sem promessa de melhoria.

### Task 4 — Cena e controlador da lan house
Files: src/lanhouse-scene.js, src/lanhouse.js, index.html, style.css, main.js, garden.js.
Interfaces: LanHouse(garden).tick(dt), render(time), setActive(bool), snapshot(), resize().
- [x] Montar sala 3D e monitor com canvas compartilhado com a tela ampliada; mesma mosca e renderizador.
- [x] Integrar demonstrar, treinar, acelerar, avaliar/cancelar, pausa, teclado/toque, exportar e reset confirmado.
- [x] Preservar sessão do jardim e desligar controles ao trocar; falha localStorage tratada.
- [x] Testar navegador: transições, ausência de treino oculto, replay, mobile, reload e erros de renderização.

### Task 5 — Revisão e publicação
Files: testes de navegação, docs, README, evidências.
- [x] npm test, npm run build, inspeção de imagens desktop/mobile e auditoria da especificação.
- [x] Registrar resultados de treinamento e instruções.
- [x] Commits personalizados, push GitHub, deploy Vercel, verificar URL pública e estado remoto.

## Ledger de execução

- Execução nativa autorizada pelo usuário; revisão final independente somente leitura realizada pelo agente review_lanhouse.
- Tarefas 1–3: testes de layout e motor/agente/avaliação passaram; treino reproduzível de 15.000 episódios registrado em docs/PONG_EVALUATION.json.
- Ruling: sementes pares para treino/demonstração e ímpares para avaliação — impede cruzamento em treino prolongado; relatório foi reexecutado nessa configuração.
- Revisão encontrou e corrigiu: Espaço em botões, validação espacial, expiração de convite, reserva de saques e totais de treino no painel.
- Testes de robustez passaram: armazenamento inválido e indisponível, exportação, foco de teclado, aba oculta simulada, troca com treino ativo, ajuda e cancelamento.
- Ruling: o jardim conserva uma clareira inicial, com flores ao longo das rotas, mantendo as experiências espalhadas; a brisa aproxima a mosca do centro antes de aplicar deslocamento para não impedir a descoberta.
- Tarefa 4: teste completo da lan house passou com demonstração real por toque, treino, avaliação sem mutação, sessão preservada e replay.
- Tarefa 5: regressão das seis experiências e verificação pública concluídas.

- Regressão completa adventures-smoke.mjs passou com seis descobertas, entrega, persistência, replay e mobile. Otimização de tiles de 600 unidades revisada independentemente; liberação dos buffers preserva geometria compartilhada.

- Última validação local: 23 testes unitários, build Vite, lanhouse-smoke (inclusive clique real no acesso 3D via visão geral), lanhouse-robustness (incluindo confirmação de reinício) e adventures-smoke passaram. Imagens de computador e celular inspecionadas.

- Produção verificada em 2026-10-22: https://flyworld-garden.vercel.app, HTTP 200, bundle index-CYBSdGqT.js correspondente ao build local. Deployment dpl_7m7hx9UvQw2nBnfCJCQaySsGUM5w. lanhouse-smoke.mjs passou também contra a URL pública, incluindo acesso 3D, demonstração, treino, avaliação imutável, retorno, recarga e toque no celular. Código publicado a partir de 227aee9; esta atualização final altera somente documentação.
