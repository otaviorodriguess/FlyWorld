# Experiências do jardim

A versão web oferece seis locais de experiência próximos à região inicial, com modelos 3D, sinalização, cores no mapa e convites no painel **Pequenas aventuras**.

| Local | Experiência |
| --- | --- |
| Banquete de néctar | Flores com néctar; uma visita concluída conta como uma refeição. |
| Gotas de orvalho | Pausa para explorar gotas sobre folhas, fora dos lagos. |
| Abrigo dos cogumelos | Descanso com animação de limpeza das antenas. |
| Jardim de pólen | Coleta de pólen visível no corpo da mosca. |
| Clareira da brisa | Brisa que desloca o corpo suavemente, respeitando colisões. |
| Dança dos vaga-lumes | Luzes animadas ao redor das flores. |

Visitar as flores de néctar depois de coletar pólen completa uma entrega. A carga é consumida e o painel registra o número de entregas. A entrega pode acontecer durante a renovação do néctar.

## Descobrir ou convidar

No modo Livre, os locais próximos podem se tornar objetivos do agente. Os botões do painel convidam a mosca a seguir uma rota calculada ao redor dos obstáculos. O caminho guiado não recebe crédito de aprendizagem Q.

Ao chegar autonomamente, a ação anterior pode receber uma recompensa artificial específica do local. A interação no local é programada: ela exige alguns segundos de permanência e depois registra a descoberta no diário. A recompensa de chegada encerra a transição Q; a pausa e as animações não são apresentadas como ações aprendidas.

As estações têm um intervalo de 60 segundos de simulação entre experiências, evitando a contagem a cada frame. O painel mostra o tempo restante quando um convite espera a renovação. As descobertas, os últimos 20 registros do diário, a carga de pólen e as entregas são salvos na mesma memória do navegador e incluídos na exportação. Os intervalos de renovação são reiniciados ao recarregar a página.

Durante replay neural, as experiências ficam pausadas e os convites desabilitados. Os modelos e recompensas são elementos artificiais do jardim; não alteram os dados gravados nem os pesos biológicos. O aplicativo Python mantém seu conjunto anterior de interações; estes seis novos locais estão na versão web.

## Verificação

```powershell
cd web
npm test
npm run build
npm run dev
# Em outro terminal, na pasta web:
node adventures-smoke.mjs
```

O teste de navegador usa Playwright Chromium (`npx playwright install chromium`) e verifica descoberta dos seis locais, entrega de pólen, persistência ao recarregar, pausa no replay e apresentação em tela de celular. Os testes unitários cobrem permanência, renovação, entrega, localização segura e rotas com obstáculos.
