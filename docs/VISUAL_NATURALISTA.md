# Visual naturalista do FlyWorld

A versão web usa modelos procedurais próprios, com proporções estilizadas inspiradas em Drosophila e em um jardim natural. Nenhum modelo externo pesado foi incorporado.

## Mosca

- Abdômen com silhueta contínua e faixas texturizadas.
- Olhos com padrão de facetas, relevo discreto e reflexos do ambiente.
- Cerdas em um único buffer de linhas, antenas ramificadas e peças bucais.
- Seis pernas articuladas e duas asas com contorno curvo, nervuras e iridescência discreta.
- Sombra de contato suave para apoiar os pés no chão.

## Ambiente

- Solo e caminhos com texturas procedurais locais.
- Árvores com troncos, galhos, copas variadas e folhas individuais.
- Flores com pétalas curvas e folhas, grama em lâminas, pedras irregulares e cogumelos com chapéus modelados.
- Lagos com reflexos do ambiente, ondas suaves, pedras, juncos e vitórias-régias.
- Luz quente, preenchimento suave e ambiente de reflexão gerado localmente.
- Placas das experiências menores, exibidas durante a atividade.

## Desempenho e compatibilidade

A vegetação e as frutas reutilizam geometrias por instanciamento. Partes estáticas da mosca e das estações são combinadas por material, mantendo pernas, asas e partículas livres para animação. A remoção de instâncias de frutas libera seus buffers, preservando materiais e geometrias compartilhadas.

A resolução de renderização é limitada a 1,5 vezes a resolução CSS em telas maiores e 1,25 em celulares. Sombras usam 1024 pixels em telas maiores e 512 em celulares no carregamento. A aparência não depende de downloads de texturas, HDRIs ou modelos de terceiros.

A aprendizagem, o replay e as seis experiências mantêm a mesma lógica. Esta atualização se aplica ao jardim web.

## Referências pesquisadas

- [Three.js — MeshPhysicalMaterial](https://threejs.org/docs/pages/MeshPhysicalMaterial.html): materiais físicos, reflexos, transparência e custo gráfico.
- [Modelo anatômico de Drosophila, Joaquin Villa](https://sketchfab.com/3d-models/3d-drosophila-fly-model-22b1ccca937a421da16f511a09042291): referência visual; o arquivo não foi incorporado.
- [Poly Haven — Xanderklinge](https://polyhaven.com/a/xanderklinge): referência de iluminação natural e materiais; o HDRI não foi incorporado.
- [Poly Haven — FAQ e licença CC0](https://docs.polyhaven.com/en/faq): referência de acervo e licenciamento.

## Verificação

```powershell
cd web
npm test
npm run build
npm run dev
# Em outro terminal, na pasta web:
node visuals-smoke.mjs
```

A verificação gráfica usa Playwright Chromium, captura imagens de computador e celular, verifica erros do navegador, as seis pernas e duas asas, o carregamento do replay e um limite de chamadas de desenho no enquadramento inicial. Esse limite não representa uma garantia de FPS para todos os aparelhos.
