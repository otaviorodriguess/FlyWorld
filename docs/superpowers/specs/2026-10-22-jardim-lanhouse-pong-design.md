# FlyWorld: jardim reorganizado e lan house com Pong

Data: 2026-10-22
Status: implementado, publicado e validado no endereço público em 2026-10-22.

## Objetivo e escopo aprovado em conversa

Melhorar o desenho da mosca e a distribuição dos elementos pelo jardim e acrescentar uma lan house em um mapa separado, onde o usuário possa ensinar Pong à mosca e observar sua aprendizagem. A conversa aprovou Pong como primeiro jogo. Esta especificação registra o desenho aprovado para a implementação.

A entrega será na versão web existente, mantendo publicação na Vercel e código no GitHub. O aplicativo Python e os dados neurais originais ficam fora desta mudança.

## 1. Mosca e organização do jardim

Refinar a silhueta do corpo, a ligação entre cabeça, tórax e abdômen, as proporções das pernas e a postura de repouso. Preservar seis pernas animadas, duas asas, olhos facetados, antenas e cerdas. A mosca deve ficar legível na câmera inicial e diante do computador, com os pés apoiados no chão ou na mesa conforme a cena. O refinamento visual não altera o corpo físico usado na locomoção.

Manter o mundo em 6.000 × 4.000 unidades e distribuir as seis experiências por áreas distintas: campo de flores, margem segura do lago, bosque de cogumelos, jardim de pólen, clareira da brisa e recanto dos vaga-lumes. Os centros das experiências devem ficar a pelo menos 600 unidades entre si, ser livres de colisões e ter rotas acessíveis a partir do início.

Distribuir frutas em pequenos grupos, árvores em bosques e pedras nas bordas; reservar corredores e uma clareira inicial para evitar a aparência de objetos espalhados uniformemente. O néctar e o pólen devem permanecer conectados por um percurso útil para a entrega. Caminhos, obstáculos, lagos, estações e minimapa usarão uma definição de layout compartilhada, eliminando o caminho senoidal duplicado entre renderização e mapa.

Adicionar indicação de destino e distância nos convites. Se uma rota falhar, informar o usuário sem mover a mosca por teletransporte ou deixar o convite travado. A área inicial terá um acesso identificável à lan house; um botão de navegação também permitirá alternar os mapas sem exigir uma longa caminhada.

## 2. Dois mapas e uma sessão preservada

Separar o local atual (Jardim ou Lan house) do modo do jardim (Livre ou Replay). Trocar de mapa pausa o local anterior e preserva seu estado em memória. Ao voltar ao jardim, manter posição, alimentos restantes e descobertas durante a sessão. O replay não controla o jogo.

Usar o mesmo renderizador WebGL, alternando cenas e câmera/controles, sem criar dois loops de animação ou contextos gráficos concorrentes. Desabilitar controles de uma cena quando a outra estiver ativa e limpar teclas pressionadas nas transições, ao abrir diálogos e ao perder o foco.

A lan house será uma sala 3D compacta, com mesa, cadeira, computador, teclado, mouse, iluminação própria e a mosca diante da tela. O jogo exibido no monitor e a versão ampliada no painel devem refletir a mesma partida, usando textura de canvas e controles acessíveis por teclado e toque. A animação das patas será uma representação da ação escolhida pelo agente; não será apresentada como controle neural biológico.

## 3. Pong de treino

A primeira versão será Pong de uma raquete contra uma parede: a bola rebate na parede oposta e nas bordas superior/inferior; a mosca move a raquete verticalmente para devolver a bola. Perder a bola ou atingir o limite de 30 segundos de simulação encerra o episódio. Exibir claramente essa modalidade na interface.

Ações: subir, ficar parado e descer. Observações: posição da raquete, posição da bola e direção/velocidade da bola, discretizadas. O agente não recebe um destino futuro calculado nem usa uma regra pronta para seguir a bola. A política começa sem conhecimento específico de Pong.

Física com passo fixo e colisões que não atravessem a raquete nas velocidades permitidas. Saques com variação reproduzível de posição e direção; sem dificuldade crescente escondida durante as comparações.

### Demonstrar

O usuário controla a raquete com setas ou botões de toque. Registrar pares de observação/ação em intervalos de decisão, com contagens por estado. Esses exemplos formam uma preferência inicial por ação e podem orientar o começo da política. Contabilizar demonstrações separadamente das atualizações por recompensa. Mostrar que o usuário está controlando a partida.

### Treinar

O agente escolhe suas próprias ações usando Q-learning e exploração decrescente. Recompensas: devolver a bola +1 e perder a bola -1; limite de tempo é truncamento, sem bônus de vitória. Não premiar apenas tempo parado. Demonstrações podem orientar estados ainda não aprendidos; valores atualizados por recompensa têm precedência. A interface informa a origem das ações.

Permitir assistir e acelerar o treino com trabalho limitado por frame, mantendo a interface responsiva. Pausa, troca de mapa e aba oculta interrompem o treino. Exibir episódios, devoluções, perdas e atualizações, com histórico resumido.

### Avaliar

Congelar pesos e demonstrações, desativar exploração e executar 100 episódios em uma sequência fixa de saques reservada à avaliação. Comparar a política atual com ações aleatórias sob a mesma sequência e regras. Apresentar devoluções médias por episódio e duração média, com os números de episódios utilizados.

Avaliação não altera Q, exemplos ou estatísticas de treino. Permitir cancelar sem mostrar resultado parcial como comparação concluída. Relatar melhora somente quando medida: se a política ainda não superar a referência, mostrar os resultados sem afirmar sucesso. O objetivo é tornar o progresso verificável; não garantir aprendizado em um número predeterminado de partidas.

## 4. Memória e compatibilidade

Manter memórias separadas: jardim na chave existente e Pong em uma nova chave versionada, flyworld-pong-v1. Salvar Q, exemplos, contagens e resumo de treino do jogo. Oferecer exportação específica de Pong e reinício explícito apenas da memória do jogo, com confirmação por ser destrutivo.

Validar tamanho, tipos e valores finitos ao carregar memórias. Arquivos inválidos não devem impedir a abertura do site. Se localStorage falhar, permitir continuar a sessão e informar como exportar.

O novo jardim terá uma versão de layout. Ao detectar memória espacial do mapa antigo, preservar a política Q, as contagens de aprendizagem e as descobertas por ID; descartar apenas coordenadas de comida e células visitadas incompatíveis, com uma mensagem explicando a atualização do mapa. Não reutilizar coordenadas antigas como se fossem válidas no novo layout.

## 5. Componentes e limites

- Layout do jardim: módulo puro compartilhado por física, experiências, minimapa e renderização.
- Motor Pong: física, saques e término de episódios, sem DOM ou Three.js.
- Agente Pong: discretização, demonstrações, política Q e checkpoints, separado do agente de navegação.
- Avaliação Pong: execução reproduzível e comparação sem mutação da política.
- Cena da lan house: apresentação 3D e monitor do jogo, reutilizando o modelo da mosca.
- Integração de sessão/UI: alternância entre mapas, controles, persistência e estados de execução.

A divisão evita acrescentar toda a lógica do jogo ao arquivo main.js atual. Os detalhes dos arquivos e a ordem das alterações serão definidos no plano após aprovação desta especificação.

Nenhuma funcionalidade desta entrega simula plasticidade do conectoma ou transforma replay em respostas ao jogo. Não haverá serviços pagos, contas adicionais ou execução de Brian2 no navegador.

## 6. Critérios de aceitação e validação

1. As seis áreas do jardim são separadas, seguras e alcançáveis; caminhos e minimapa correspondem ao layout físico.
2. A mosca permanece reconhecível, articulada e visível nas duas cenas. Imagens de computador e celular serão inspecionadas.
3. Trocar entre jardim e lan house preserva a sessão e não causa controles cruzados, treino oculto ou vazamento de renderizadores.
4. Pong permite demonstração humana, treino autônomo, pausa, exportação e avaliação identificados na interface.
5. Testes determinísticos cobrem colisões, fim de episódio, atualizações Q, demonstrações, restauração e ausência de mutação na avaliação.
6. A comparação usa 100 episódios para cada política com saques correspondentes; os resultados reais, favoráveis ou não, aparecem sem seleção conveniente de partidas.
7. Testes existentes de jardim/replay continuam passando; navegação automatizada cobre transições, controles de toque e teclado, armazenamento e erros gráficos.
8. O build de produção passa e a versão publicada carrega pelo endereço público, mantendo os créditos e a licença.

## Revisão da especificação

Escopo restrito a dois mapas e um jogo. Não inclui jogos adicionais, multiplayer ou treinamento biológico. Modos de partida, ações, recompensas, saques, persistência e critérios de avaliação estão definidos. A promessa de resultado é implementar e medir o treinamento, e não afirmar antecipadamente que o agente já aprendeu.

Implementação executada pelo plano correspondente, com revisão independente e evidências em docs/LANHOUSE_VALIDACAO.md.
