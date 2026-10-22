# Lan da Mosca: ensinar Pong

Na versão web, selecione **Lan house** no topo ou clique no acesso sinalizado na clareira inicial. A sala usa o mesmo renderizador e o mesmo modelo da mosca do jardim. O monitor 3D e o painel ampliado mostram a mesma partida.

## Demonstrar

Clique **1 · Demonstrar**. Use as setas para cima/baixo ou mantenha os botões de toque pressionados. Cada decisão registra o estado observado e sua ação. Esses exemplos orientam estados ainda não aprendidos; não contam como atualizações por recompensa. Espaço pausa quando o foco estiver no cenário.

## Treinar

Clique **2 · Treinar**. A mosca controla a raquete usando Q-learning e exploração. Cada devolução rende +1, cada perda −1. As partidas terminam ao perder a bola ou após 30 segundos, sem bônus pelo limite de tempo. O seletor acelera a simulação, limitado pelo orçamento de trabalho do navegador; “até 1000×” não garante essa velocidade em todos os aparelhos.

O painel mostra partidas, exemplos, atualizações Q, totais de devoluções e perdas, média das últimas 100 partidas e histórico. Trocar para o jardim, ocultar a aba, pausar ou abrir a ajuda interrompe os passos de jogo/treino.

## Avaliar

Clique **3 · Avaliar sem aprender**. A política fica congelada e sem exploração e é comparada a ações aleatórias: 100 episódios de cada política, com os mesmos saques. Os saques de avaliação usam sementes ímpares reservadas; treino e demonstrações usam sementes pares. É possível cancelar, sem apresentar a parte executada como avaliação completa.

A avaliação não atualiza Q, demonstrações ou estatísticas de treino. O texto mostra as devoluções e o tempo médio realmente medidos; não garante que qualquer agente supere a referência após um número fixo de partidas.

## Memória

A chave de armazenamento Pong é `flyworld-pong-v1`, separada do jardim. Use **Exportar memória Pong** para obter o checkpoint. **Reiniciar Pong** exige confirmação e não apaga o jardim. Memórias inválidas são ignoradas; se o armazenamento falhar, a sessão continua e a exportação fica disponível.

A troca entre mapas preserva a posição e a sessão do jardim. A memória espacial do jardim anterior é renovada na migração do layout; a política, os contadores e as descobertas são preservados.

## Experimento reproduzível

```powershell
cd web
node benchmark-pong.mjs
```

O script começa com uma política nova, treina 15.000 episódios (semente base 17) e compara antes/depois com a mesma sequência reservada de 100 saques. O resultado completo está em [PONG_EVALUATION.json](PONG_EVALUATION.json). Na execução registrada: política treinada **2,36 devoluções por episódio**, referência aleatória **0,39**, sem demonstrações humanas. A política inicial marcou 0,40; essa diferença pequena isolada não constitui evidência de aprendizagem. O ganho observado após treino é deste experimento, não uma garantia para toda sessão.

Nenhum checkpoint treinado é instalado silenciosamente no navegador: a memória nova de Pong começa sem aprendizagem específica. Esta é uma habilidade de um agente artificial; Brian2 e o conectoma biológico não controlam o Pong nesta versão.
