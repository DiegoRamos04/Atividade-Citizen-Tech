# IncluiSP

Aplicação web responsiva de mobilidade e acessibilidade urbana em São Paulo. Projeto FIAP Global Solution — CitizenTech 2026.

## Executar localmente

É necessário ter Node.js 24 ou superior. No PowerShell, a partir da pasta do projeto, execute:

```powershell
npm.cmd ci
npm.cmd start
```

Abra [IncluiSP no navegador](http://127.0.0.1:3000). O mapa, a busca externa e o cálculo de percursos usam serviços pela internet. O catálogo, o perfil, os benefícios, as consultas do assistente e o cadastro de ocorrências com pontos selecionados no catálogo continuam disponíveis sem esses serviços.

O servidor reinicia automaticamente quando os arquivos do servidor ou a base de dados do catálogo mudam. Atualize a aba para ver as alterações.

## Demonstração

1. Em **Meu perfil**, selecione cadeira de rodas, ative a preferência de evitar escadas e salve.
2. Em **Rotas e mapa**, selecione **Estação Consolação** na origem e **MASP** no destino. Busque rotas e abra **Descrição do percurso**. O número de alternativas depende do serviço.
3. Em **Lugares**, filtre por **Banheiro adaptado**. Abra um local no mapa ou use-o como destino.
4. Em **Benefícios**, consulte as condições de ingressos e visitação. Em **Inclui IA**, também é possível perguntar sobre o Bilhete Único Especial e consultar a fonte.
5. Em **Ocorrências**, informe uma barreira, use **Buscar endereço** para selecionar o ponto e envie. Consulte o status em **Minhas ocorrências**.

### Moderação

Para ativar a fila em uma instância local, defina uma chave antes de iniciar o servidor:

```powershell
$env:INCLUISP_MODERATOR_KEY = 'substitua-por-uma-chave-longa-e-aleatoria'
npm.cmd start
```

Abra **Moderação** no rodapé, informe a chave e carregue a fila. Confira o relato e a foto, revise o tipo, o local e a descrição, registre a decisão e o motivo. Relatos aprovados aparecem no mapa e são considerados no planejamento quando estão a até 25 metros da geometria da rota. A proximidade é um alerta para verificar o local e pode incluir obstáculos do lado oposto da rua. A foto e o motivo da revisão ficam fora da listagem pública.

Em **Lugares**, use **Sugerir um lugar**. O navegador acompanha as sugestões que enviou, e a chave acima dá acesso à fila da equipe. Ao aprovar uma sugestão, o local aparece no catálogo e no mapa com a identificação da comunidade. A foto enviada é publicada após a aprovação. Quando falta foto, o card usa a imagem padrão da comunidade.

O autor acompanha a ocorrência pelo navegador usado para criá-la. O vínculo é mantido em um cookie HTTP-only. O catálogo e o mapa funcionam sem cadastro. O perfil de mobilidade é salvo no navegador e pode ser apagado em **Meu perfil**.

## Dados e limites do MVP

| Módulo | Implementação |
| --- | --- |
| Mapa e endereços | Leaflet com mapa de ruas do OpenStreetMap. Busca no catálogo com complemento do geocodificador Photon. |
| Catálogo e benefícios | Fotos com créditos nas duas abas. Algumas imagens carregam do site que publicou a foto. Os filtros incluem restaurantes com rampa de entrada, hospitais próximos e locais com gratuidade ou desconto. |
| Hospitais próximos | Os hospitais do catálogo são ordenados por distância em linha reta a partir da localização autorizada, da origem do trajeto ou do MASP como referência inicial. |
| Rotas | Valhalla para trajetos de ruas a pé ou em cadeira de rodas, com preferência por distância, inclinação e evitar escadas conforme os dados do provedor. A distância confortável gera um alerta e influencia a ordem dos resultados. |
| Confiabilidade | As rotas indicam barreiras documentadas próximas ou informações insuficientes. O MVP ainda precisa de evidência sobre todos os trechos para atribuir acessibilidade verificada. |
| Transporte | Busca paginada por estações, terminais e pontos. Os resultados podem abrir no mapa e virar destinos do planejador. Status em tempo real dos elevadores, veículos acessíveis por viagem e cálculo multimodal dependem de integrações futuras. |
| Inclui IA | Recuperação de respostas prontas na base local `data/base.json`, com fontes e resposta de insuficiência quando a base não cobre a pergunta. A versão roda sem modelo generativo e sem chave de IA. |
| Benefícios | Registros públicos, condições de visitação e descontos com fontes. Uma oferta com data de expiração deixa de aparecer após essa data. |
| Ocorrências | SQLite para persistência local, fila de moderação e foto opcional. |

O arquivo `data/transit.json` reúne localizações das camadas de [estações de metrô, terminais e pontos de ônibus do GeoSampa](https://novogeosampa.prefeitura.sp.gov.br/), sob [CC BY-SA](https://creativecommons.org/licenses/by-sa/4.0/). A base foi convertida para coordenadas decimais e complementada com estações verificadas no [mapa da rede](https://www.metro.sp.gov.br/sua-viagem/mapa-da-rede/) e terminais da [SPTrans](https://www.sptrans.com.br/terminais). É um retrato da rede consultada em novembro de 2026. Consulte as operadoras para confirmar horários e alterações.

O servidor escuta apenas em `127.0.0.1` por padrão. A porta pode ser alterada com `PORT`. `INCLUISP_DB`, `INCLUISP_VALHALLA` e `INCLUISP_PHOTON` permitem configurar o arquivo de dados e os provedores. O banco padrão fica em `.local/incluisp.sqlite`.

## Validar

```powershell
npm.cmd test
```

Os testes cobrem geometria e classificação, aplicação de preferências e alternativas, indisponibilidade do roteador, busca geográfica, fontes do assistente e o fluxo de avaliação das ocorrências. A avaliação com participantes do público-alvo prevista no PRD permanece pendente.
