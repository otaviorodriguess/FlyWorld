# Mundo 3D

**Atualização:** o jardim foi ampliado para 6.000 × 4.000 unidades e ganhou interações. Consulte [JARDIM_INTERACOES.md](JARDIM_INTERACOES.md) para os controles atuais; as medições abaixo correspondem à primeira versão 3D.

A visualização padrão agora é 3D: malhas em coordenadas XYZ, projeção em perspectiva, iluminação direcional, ordenação de profundidade, asas translúcidas, sombra de contato e câmera orbital. Usa NumPy e Pygame em CPU, sem instalar motor/GPU adicional. O cenário é um pequeno jardim com grama, pedras, folhas, frutas verdes e cogumelos sobre os obstáculos sólidos.

A mosca foi modelada proceduralmente: abdômen com faixas, tórax, cabeça, olhos vermelhos com reflexos, antenas, cerdas, duas asas com nervuras e seis pernas articuladas. A animação depende do movimento do corpo; ela não produz nem representa spikes.

```powershell
.\.venv\Scripts\python -m flyworld --mode demo
.\.venv\Scripts\python -m flyworld --mode replay --spikes flyworld-output/p9-on.parquet
.\.venv\Scripts\python -m flyworld --view 2d
```

- Roda: aproximar/afastar.
- A/D ou arrastar o botão central: girar a câmera.
- W/X: inclinação.
- C: alternar entre seguir a mosca e visão geral da arena.
- F: mostrar/ocultar os sensores geométricos.
- V: alternar visualização 3D/2D durante a execução.
- Clique esquerdo/direito: comida/obstáculo, usando interseção de raio com o chão.
- H: todos os controles anteriores continuam disponíveis.

A câmera começa próxima da mosca para mostrar seu corpo. C mostra a arena inteira. Demo, replay e live compartilham a mesma cena, com o dashboard neural preservado. A física continua sendo caminhada no plano: não foram adicionados voo, gravidade ou interpretação neural de altitude. Folhas/grama são decorativas; cogumelos ficam nos obstáculos que já têm colisão.

A geometria estática é armazenada em cache e as transformações/projeções são vetorizadas. Um ensaio local headless de 15 quadros, após aquecimento, mediu aproximadamente 16 FPS no renderizador CPU; o desempenho varia com zoom, tamanho da janela e hardware. O limite do loop é 60 FPS, sem promessa de atingir essa taxa. Para máquinas lentas use V ou `--view 2d`. O renderizador usa ordenação de faces em vez de z-buffer; objetos interpenetrantes podem apresentar pequenos artefatos de oclusão.

Testes adicionais verificam projeção/interseção do chão em vários ângulos, clique em 3D, cache/invalidação do cenário, câmeras e alternância de renderizador sem alterar física/adaptador neural. Capturas: `mundo3d.png` (próxima) e `mundo3d-geral.png` (arena).
