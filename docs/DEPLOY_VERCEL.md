# FlyWorld na Vercel

A pasta web contém uma versão independente para navegador: Three.js, jardim 6000 × 4000, interações, Q-learning artificial e memória em localStorage. A política inicial vem do checkpoint artificial local. As experiências futuras são salvas separadamente em cada navegador.

As seis amostras neurais públicas foram exportadas de Parquets reais do arquivo nature_2026_07.zip: açúcar, 200 Hz, 1 segundo, trial 0, seis backends. Cada JSON inclui o SHA-256 do Parquet original. O raster mostra uma amostra dos 16 neurônios mais ativos. O replay não constitui execução live e não transforma spikes arbitrários em movimento.

O cérebro completo Brian2 e o arquivo de 20 GB permanecem no aplicativo Python local. Somente a pasta web é enviada à Vercel.

## Desenvolvimento e verificação

```powershell
cd web
npm ci
npm test
npm run build
npm run dev
node smoke.mjs
```

O teste smoke usa Playwright; instale o navegador com `npx playwright install chromium`. Para testar uma implantação, defina FLYWORLD_URL com a URL pública antes de executar o teste.

## Publicação

Projeto Vercel: tavinnew/flyworld-garden. A autenticação é gerenciada pelo Vercel CLI, sem credenciais nos arquivos do projeto.

```powershell
cd web
vercel --prod --yes
```

A associação local está em web/.vercel e não deve ser versionada. O projeto não está conectado ao repositório upstream no GitHub, pois não temos permissão de escrita nele. A implantação é feita pelo CLI.

URL de produção: https://flyworld-garden.vercel.app
