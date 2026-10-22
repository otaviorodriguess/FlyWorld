# Jardim ampliado e interações

O mundo principal passou de 1.200 × 800 para **6.000 × 4.000 unidades: 25 vezes a área anterior**. A mosca começa em uma clareira central, cercada por caminhos, árvores, flores, cogumelos, frutas e lagos com lírios. A geração usa semente fixa. O mundo não termina na região visível: a câmera acompanha a mosca durante a exploração.

O visual usa cores de jardim ao sol, destaque âmbar no corpo da mosca, olhos vermelhos, asas translúcidas com nervuras, iluminação e névoa de distância. O painel tem hierarquia mais simples e as ações ficam em uma barra permanente sobre o cenário. A modelagem continua procedural, local, sem baixar modelos ou usar APIs.

## Interagir

| Opção | Ação |
|---|---|
| **Oferecer fruta / B** | Coloca uma fruta em um ponto livre à frente da mosca. No demo, ela tenta alcançá-la. |
| **Chamar até aqui** | Cria um marcador; depois clique no chão ou no minimapa para indicar um destino. |
| **Fazer carinho / K** | No demo, para por quatro segundos de simulação e anima as pernas dianteiras perto das antenas. Também pode clicar próximo da mosca após selecionar a ferramenta. |
| **Brincar com luz / J** | Mostra uma luz móvel e, no demo, tenta segui-la; clique no cenário para mudar o centro da brincadeira. |
| **Explorar livre / L** | Encerra a interação guiada e devolve o controle ao explorador heurístico. |

As reações são **lúdicas, artificiais e heurísticas**. Não representam afeto, aprendizagem, consciência ou circuitos biológicos validados. O manual tem prioridade sobre as interações. No live/replay, a política de interação nunca substitui o comando neural: marcadores e animações são visuais. Frutas continuam sendo objetos físicos e podem gerar o estímulo virtual sugar no live, conforme proximidade; o replay permanece imutável.

O chamamento e a brincadeira usam direção ao alvo e prevenção local de obstáculos, sem planejamento global de rotas. Um destino do outro lado de um lago pode exigir outro marcador ou controle manual. Alvos dentro da água/obstáculos são recusados. As águas têm colisão elíptica aproximada com margem para o corpo.

## Navegar pelo mapa

- **C**: alterna câmera próxima e visão geral do mundo inteiro.
- **Roda**: zoom; **A/D** ou botão central arrastado: rotação; **W/X**: inclinação.
- **Minimapa, clique esquerdo**: chamar até a região indicada, no demo.
- **Minimapa, botão direito**: visitar visualmente a região, sem teleportar a mosca nem modificar sua posição. C retorna à câmera que acompanha a mosca.
- **V**: alternar 3D e mapa 2D; **H**: ajuda.

## Arquitetura e registro

`World.garden()` cria o mapa ampliado; `World()` continua disponível como arena pequena para componentes e testes. `interactions.py` mantém ação, destino, duração e controle heurístico limitado ao demo. Botões, atalhos e minimapa usam a mesma entrada `App.interact()`. Os eventos são salvos em `interactions.jsonl` na sessão; `telemetry.csv` também identifica a ação ativa. Não são fabricados spikes para representar interações.

O renderizador constrói detalhes só perto da região observada e reduz os detalhes na visão geral. Terreno/vegetação ficam em cache por região; frutas têm cache separado. O índice espacial de obstáculos evita testar todos os objetos a cada raio sensorial. Construção de novas regiões/edição de obstáculos ainda é síncrona e pode causar uma pequena pausa. O renderizador usa CPU e ordenação de faces, com os limites de oclusão já descritos em MUNDO_3D.md.

Em uma medição headless local de 15 quadros, com atualização física, foram observados cerca de **14,8 FPS**; o terreno permaneceu em cache durante o movimento. Construção inicial de cena foi aproximadamente 0,64 s; oferta de fruta, com terreno em cache, aproximadamente 0,07 s. São medições curtas nesta máquina, não garantia de desempenho. A caminhada permanece no chão; não foi implementado voo.

## Validação

A suíte foi ampliada com testes de tamanho do mundo, colisões na água, índice espacial comparado à geometria direta, duração das interações, isolamento de live/replay, botões, minimapa e eventos em disco. Também foram executados demo e replay com captura de tela. Os scripts neurais originais continuam preservados.
