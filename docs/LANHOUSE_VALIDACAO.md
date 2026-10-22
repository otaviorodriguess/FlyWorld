# Validação — jardim e lan house

## Evidências por requisito da especificação

| Requisito | Evidência |
| --- | --- |
| Seis áreas separadas e seguras | layout.test.js verifica distância mínima de 600 unidades, colisões e rotas desde a clareira. |
| Caminhos compartilhados | layout.js fornece os mesmos pontos usados por scenery.js e drawMap em main.js. world.json é gerado dessa definição. |
| Memória espacial antiga | testes de migração preservam Q/contadores/descobertas e descartam apenas coordenadas incompatíveis; testes de corrupção rejeitam coordenadas e contagens inválidas. |
| Mosca nas duas cenas | mesmo objeto fly e sombra migram entre cenas, com pose de teclado; seis pernas e duas asas preservadas. Imagens de navegador em test-results são inspecionadas. |
| Uma sessão/renderizador | lanhouse-smoke.mjs verifica um canvas WebGL e restauração exata da posição/tempo do jardim pausado após visitar a sala. |
| Demonstração humana | teste de teclado e toque real pelo protocolo do navegador verifica deslocamento e exemplos sem atualizações Q. |
| Treino independente | testes do agente e navegador mostram atualizações Q e partidas; memória Pong separada, sem modificar Q do jardim. |
| Avaliação reproduzível | testes verificam 100 episódios por política, saques iguais e checkpoint original inalterado. Treino usa sementes pares; avaliação usa ímpares. |
| Aprendizagem medida | benchmark-pong.mjs, 15.000 episódios, resultado em PONG_EVALUATION.json: 2,36 devoluções da política treinada e 0,39 da referência. |
| Cancelamento | teste puro e teste de UI cancelam sem resultado final nem alteração de pesos. |
| Pausa e isolamento | navegador testa saída durante treino ativo, ocultação simulada e diálogo; passos param e teclas são limpas. |
| Persistência e falhas | navegador testa recarga, arquivos inválidos, quota bloqueada e exportação disponível. |
| Regressão do jardim | testes unitários existentes passam; brisa testada em oito direções de chegada. O teste completo das experiências percorre os destinos. |
| Publicação | conferir commit remoto e URL pública após o deploy; registro final no ledger do plano. |

23 testes unitários e os cenários completos de navegação passaram. A revisão independente confirmou as correções de memória, foco, convites, saques reservados e limpeza de buffers.

## Comandos

```powershell
cd web
npm test
npm run build
node benchmark-pong.mjs
npm run dev
# Outro terminal, mesma pasta:
node lanhouse-smoke.mjs
node lanhouse-robustness.mjs
node adventures-smoke.mjs
```

Testes de navegador usam Playwright Chromium (`npx playwright install chromium`). Resolução reduzida no navegador automatizado permite validar WebGL por software; não constitui benchmark de FPS em aparelhos reais. A avaliação descreve uma amostra controlada, não uma promessa de capacidade biológica ou desempenho garantido em toda sessão.
