# Wakely

Protótipo acadêmico da Insper AI que detecta sonolência ao volante com câmera e deep learning. **Não é um dispositivo de segurança e nunca deve ser testado dirigindo.**

Este arquivo resume o estado do projeto em 06/11/2026, depois da seção 8 (modelo temporal, branch `feat/modelo-temporal`). A pesquisa completa está em `docs/pesquisa_wakely.md`, e o código e os resultados, em `wakely.ipynb`.

Prazos: apresentação intermediária em 12/11/2026, entrega final (notebook e paper) em 17/11/2026 e apresentação final em 18/11/2026.

## Como rodar

```bash
uv sync
uv run jupyter nbconvert --to notebook --execute --inplace wakely.ipynb --ExecutePreprocessor.timeout=-1
```

- Com o cache pronto e a pasta `len60` baixada, a execução leva cerca de 8 minutos em uma RTX 3050.
- Sem cache, leva cerca de 1 hora, com download de cerca de 1,7 GB, extração com o MediaPipe e 11 treinos.
- `data/` fica fora do Git. Ela guarda os dados, `data/cache/` (sinais e recortes) e `data/modelos/` (pesos).
- Para refazer a extração do FL3D, é preciso apagar os arquivos `fl3d_*` de `data/cache/`.
- A seção 8 baixa a pasta `len60` do UTA-RLDD (1,2 GB) e extrai os sinais em cerca de 2,5 h na CPU de um Apple M5, com cache por pessoa em `data/cache/rldd/`. Como as pessoas são independentes, a extração foi rodada em 4 processos com `extrair_pessoa`. As previsões da GRU e da TCN ficam em `data/cache/rldd_temporal/`. Apague essas pastas para refazer.

## Pipeline atual

Webcam → MediaPipe → P(olho fechado) ou EAR → filtro de bocejo → regra de tempo → alerta.

- **Regra de alerta:** olho fechado por T = 1 s, o limite inferior da faixa de microssono do Euro NCAP. Há também os níveis de 3 s (sono) e 6 s (sem resposta), ainda pouco testados.
- **Filtro de bocejo:** ignora o olho fechado durante um bocejo detectado pela abertura da boca. Usa só frames passados, para valer também ao vivo.
- **Piso de 3 s (proposto):** olho fechado por 3 s ou mais dispara o aviso forte mesmo durante bocejo, para não silenciar quem dorme de boca aberta. Foi testado na seção 7 (custa 2 alarmes com o YOLO nos 44 vídeos), mas ainda não entrou na regra das seções 2 a 6.
- **Agente de RL (seção 7):** é um experimento. Ele não supera a regra e não faz parte do pipeline.
- **Modelo temporal (seção 8):** GRU e TCN sobre 1 minuto de sinais, no UTA-RLDD. Não superam o PERCLOS do minuto e ficam fora do pipeline. O candidato para o aviso de sonolência é o PERCLOS.
- **Ainda não existe:** a demo com webcam.

## Estrutura do notebook

| Seção | Conteúdo |
| --- | --- |
| 1 | Configuração e dados: MRL Eye, FL3D |
| 2 | Linha de base: MediaPipe, EAR, regra de alerta e varredura de T |
| 3 | MobileNetV3-Small no MRL Eye, com divisão por pessoa |
| 4 | CNN no vídeo e ajustes do sinal (4.2), com validação cruzada |
| 5 | Comparação entre MobileNetV3 e YOLO26n-cls, com 5 sementes |
| 6 | Falsos alarmes: filtro de bocejo (6.1) e piscadas via NITYMED (6.2) |
| 7 | Agente de RL no alerta: Q-learning com tabela, curva por λ, tecla "foi alarme falso" e mapa da política |
| 8 | Modelo temporal no UTA-RLDD: extração (8.1), análise inicial e falsos alarmes (8.2), PERCLOS e logística (8.3), GRU e TCN (8.4) |
| 9 | Resumo e próximos passos |

Funções principais: `fechamento`, `bocejo_ativo`, `alertas` e `avaliar_eventos` (seção 2), `treinar` e `prever` (seção 3), `contagens` e `deixar_um_video_de_fora` (seção 4.2), `rodar_agente`, `rodar_regra` e `treinar_agente` (seção 7), `extrair_pessoa`, `atributos`, `avisos_regra`, `metricas_8` e `prever_temporal` (seção 8).

As saídas gravadas vêm de uma execução completa na RTX 3050 do Rafael, em 06/11/2026. As seções 1 a 6 reproduziram as saídas originais, e a seção 7 mudou nos números do YOLO (veja Resultados). A seção 8 usa os caches `rldd/` e `rldd_temporal/` gerados pela Luana na CPU de um Apple M5, com os pesos do YOLO da semente 42 do Rafael. Isso foi conferido em 2 clipes: o P(fechado) do cache tem correlação de 0,99 com essa semente, contra 0,72 a 0,87 com as sementes 1 e 2. A diferença que sobra deve vir do MediaPipe em Mac e em Windows, então uma extração nova deve ser feita toda numa máquina só. Numa execução completa no M5, as seções 3 a 6 mudaram um pouco (por exemplo, os falsos alarmes do YOLO com filtro foram de 10,2 para 9,4), porque CPU e GPU arredondam as contas de forma diferente.

## Dados

| Base | Uso |
| --- | --- |
| MRL Eye | Treinar os classificadores de olho. Infravermelho, 37 pessoas |
| FL3D | Avaliar em vídeo, com rótulo por frame. 44 vídeos, sem piscadas. Os 5 vídeos de holdout são o teste, e os outros 39, a calibração |
| NITYMED | Vídeos originais do FL3D, usados para recolocar os frames removidos |
| UTA-RLDD recortado | Seção 8: só a pasta `len60`, com 1.136 clipes de 1 min a 10 fps, de 60 pessoas, alertas ou sonolentas (falta a sonolenta da pessoa 42). Os clipes de cada vídeo são minutos seguidos, e os 10 com menos de 600 frames são o último de cada vídeo |

## Decisões

- **T = 1 s fixo.** T = 0,4 s vencia só porque o FL3D não tem piscadas. Ele fica apenas na varredura, como referência otimista.
- **Filtro de bocejo (opção 2, escolhida pelo grupo):** ignorar o olho fechado durante o bocejo, em vez de só reportar à parte, exigir mais tempo ou dar um aviso mais leve.
- **Repositório público e licença AGPL-3.0,** o que atende à exigência da `ultralytics`.
- **Figuras com recortes de olhos ficam no notebook,** para mostrar os dados, com as fontes citadas.
- **Não treinar CNN do zero.** Os classificadores usam fine-tuning a partir do ImageNet. Do zero, só o modelo temporal.
- **YOLO detector e SAM 2 estão fora do pipeline.** A pergunta sobre isso à organização ainda está em aberto.
- **Agente de RL fica como experimento.** A demo usa a regra (YOLO, T = 1 s, filtro de bocejo), e a sugestão é somar o piso de 3 s.
- **Modelo temporal:** janela de 60 s, entradas P(fechado), EAR, boca e rosto, e YOLO da semente 42. Os atributos da seção 8.2 e os hiperparâmetros da GRU e da TCN foram fixados antes de ver os resultados e não devem ser ajustados olhando as dobras de teste.
- **Linha de base por pessoa (primeiro minuto alerta como referência):** fica para uma próxima etapa, de produção.

## Resultados

Com T = 1 s, nos 44 vídeos, contando episódios de 1 s ou mais (165). Classificadores com média de 5 sementes.

| Sinal | Recall sem filtro | Falsos sem filtro | Recall com filtro | Falsos com filtro |
| --- | --- | --- | --- | --- |
| EAR | 79,4% | 39 | 85,5% | 16 |
| MobileNetV3-Small | 73,5% | 41 | 76,0% | 18 |
| YOLO26n-cls | 84,5% | 33 | 86,8% | 10 |

- **Classificadores:** o YOLO supera a MobileNet em recall, com filtro (+10,8 pontos, intervalo de +3,5 a +19,8). Ele não supera o EAR de forma conclusiva (+1,3 pontos, intervalo de -7,5 a +13,7).
- **No MRL, em 8 pessoas novas:** acurácia de 97,7% no YOLO e 96,8% na MobileNet.
- **Filtro:** com o mesmo limiar de olho, não perdeu microssonos na calibração. Parte do ganho de recall vem de um limiar mais baixo, que também aumenta os alarmes fora de bocejo.
- **Agente de RL (seção 7, linha do tempo completa, 11 dobras por vídeo, 5 sementes):** não supera a regra em nenhum λ. Com YOLO e λ = 10, acha 148,6 de 165 episódios de 1 s ou mais com 13,4 falsos alarmes (2,2 fortes), contra 149 e 10 da regra com piso. Esses números do YOLO mudam com a GPU: numa RTX 4060, foram 143 e 15,4 (4,2 fortes), enquanto os do EAR e da regra não mudaram. Por isso, diferenças de poucos episódios entre o agente e a regra não contam. Aprende sozinho a ignorar o bocejo e avisa com 0,8 s quando já houve 3 ou mais fechamentos longos no último minuto. A tecla simulada tira até 23% dos falsos alarmes no mesmo λ, mas nenhum com YOLO e λ = 10.
- **Piso de 3 s ignorando o filtro de bocejo:** custa 2 alarmes com o YOLO e 22 com o EAR, nos 44 vídeos.
- **Piscadas (YOLO, semente 42, com filtro, 46 min):** 8 alarmes atravessam os 710 buracos de até 0,5 s, cerca de 1%. No total são 27 alarmes, dos quais 17 estão em buracos longos sem rótulo.
- **Falsos alarmes em pessoas acordadas (seção 8.2, UTA-RLDD, 9,5 h, regra da demo a 10 fps):** 6,7 por hora (IC95% de 0,7 a 16). 54 das 60 pessoas não têm nenhum, uma pessoa dá 40 dos 64, e as 5 com mais alarmes somam 97%. As 3 primeiras têm EAR de olho aberto de 0,19 a 0,20, contra 0,25 da mediana. Na classe sonolenta, são 63 alarmes por hora.
- **Sonolência em 1 minuto (seção 8, 5 dobras por pessoa, 1.126 clipes):** PERCLOS com limiar AUC 0,774; regressão logística 0,746; GRU 0,750 ± 0,009; TCN 0,754 ± 0,014 (5 sementes). Nenhuma diferença é conclusiva (GRU - PERCLOS: -0,024, de -0,059 a +0,012). Por vídeo, a GRU acerta 74,6%, e o PERCLOS, 65,5%. O artigo da base fez 65,2% por vídeo, com 3 classes e outro protocolo.

## Cuidados

- **Holdout:** não ajustar nada olhando o holdout. Ele tem só 2 vídeos com microssono, e seus resultados já foram vistos nas avaliações anteriores, então trate-o como confirmação fraca.
- **Motoristas:** 3 dos 5 motoristas de validação e teste do FL3D são inéditos, e os outros 2 aparecem no treino dos autores. A base não tem identificador de motorista, então a validação cruzada é por vídeo.
- **Separação por pessoa:** é obrigatória em qualquer treino novo.
- **Variação entre treinos:** com a mesma semente, em outra GPU, a AUC-PR da MobileNet no vídeo variou de 0,65 a 0,76. Compare modelos com várias sementes.
- **Ponto cego do filtro:** a base não mostra microssono junto de bocejo, porque cada frame tem um único rótulo. Falar ou rir também pode ativar o filtro.
- **Rótulo e roteiro:** 35% dos episódios do FL3D duram menos de 1 s, e os vídeos parecem seguir um roteiro.
- **Falsos alarmes:** a taxa de bocejo não representa uma viagem. Reporte alarmes em bocejo e fora de bocejo separadamente, cada um com o próprio denominador.
- **Gravações do grupo servem só para teste.** Treinar, escolher limiar ou escolher T com elas faz o sistema decorar quem gravou. Se mais de uma pessoa gravar, avalie deixando uma pessoa de fora por vez. A calibração do primeiro minuto e a tecla de alarme falso são personalização na hora do uso e não contam como overfitting, desde que a avaliação seja feita em outra pessoa.
- **Vídeos da internet (YouTube etc.):** não usar. Os termos de uso proíbem baixar, e são rostos sem consentimento (LGPD). Para medir falsos alarmes em pessoas acordadas, use bases públicas, como a classe alerta do UTA-RLDD, o YawDD ou o DMD.
- **UTA-RLDD:** o rótulo é autorrelatado e vale para o vídeo inteiro, e cada classe foi gravada num dia diferente. O EAR de olho aberto é menor no sonolento em 73% das pessoas, o que pode ser pálpebra caída ou diferença de câmera. A 10 fps, uma piscada dura de 1 a 4 frames, então parâmetros em frames da seção 6 precisam ser convertidos pelo tempo (`em_rldd`).
- **Viés do limiar único:** os falsos alarmes em pessoas acordadas se concentram em quem tem o olho aberto menor na imagem, seja pela anatomia, pelo ângulo da câmera ou pelo olhar.
- **Reprodutibilidade:** o teste de alinhamento com o NITYMED (264 amostras), a inspeção visual dos recortes, a checagem de continuidade dos clipes do UTA-RLDD e a olhada nos frames das pessoas com mais alarmes foram feitos fora do notebook. Ele só registra as conclusões.

## Convenções

- Não versionar dados, vídeos, recortes soltos, caches nem pesos. O `.gitignore` já cobre isso.
- Não versionar segredos. O repositório é público.
- Trabalhar em branch com PR. Conflitos em `.ipynb` são difíceis de resolver, então avise o grupo antes de editar o notebook.
- Depois de mudar código no notebook, executar tudo e conferir se os números do texto, do resumo (seção 9) e do `README.md` batem com as saídas.
- Gravações do grupo só em local seguro, na mesa ou em carro desligado e parado, e depois de consultar o orientador sobre LGPD e ética.

## Próximos passos

1. **Modelo temporal com entrada mais rica (proposta, a fechar com a Luana):** acrescentar posição da cabeça e um grupo pequeno de blendshapes do MediaPipe, dar o PERCLOS e os atributos também à rede (entrada híbrida) e testar um transformer pequeno ao lado da GRU e da TCN. A logística recebe os mesmos sinais novos, para a comparação ser justa, e um teste de controle com atributos parados do clipe mede o atalho do dia da gravação. Protocolo fixado antes de rodar.
2. **Demo com webcam (para 12/11):** regra com YOLO, filtro de bocejo e piso de 3 s, FPS reais, estado "sem rosto visível" e os três níveis de alerta. O aviso de sonolência pode usar o PERCLOS do último minuto, com a webcam reamostrada para 10 fps.
3. **Falsos alarmes em situações difíceis:** gravações encenadas do grupo, só como teste, com conversa, olhares para baixo e bocejos com olho fechado, incluindo microssono encenado junto de bocejo.
4. **Piso de 3 s na regra principal:** levar o piso da seção 7 para a seção 6 e conferir os números.
5. **Linha de base por pessoa (próxima etapa):** primeiro minuto alerta como referência, no UTA-RLDD, para os falsos alarmes concentrados e para o PERCLOS.

## Pontos fracos atuais

- **Sonolência antes do microssono:** o PERCLOS do minuto separa alerta de sonolento com AUC de 0,77 entre pessoas, mas a GRU e a TCN não acrescentam nada, e o rótulo do UTA-RLDD é autorrelatado.
- **Teste pequeno:** o holdout tem 2 vídeos com microssono, e a validação cruzada é por vídeo, não por motorista.
- **Falso alarme medido só parado:** a taxa de 6,7 por hora vem de pessoas acordadas gravando a si mesmas, sem dirigir, a 10 fps, e depende muito de quem está na câmera. Não vale para uma viagem.
- **Redes × EAR:** nenhum classificador supera o EAR de forma conclusiva. O treino é em infravermelho (MRL) e o teste em RGB.
- **Recorte do olho:** fica torto quando a cabeça cai, justamente no microssono.
- **Agente de RL:** tem poucos dados por pessoa (vídeos de 20 s a 2 min) para aprender a personalizar.

## Pendências menores

- `GroupKFold` no MRL: a divisão por pessoa ainda é uma só, e as sementes não medem a variação entre grupos de pessoas.
- MediaPipe separado por óculos, pouca luz e cabeça inclinada.
- Alinhar o recorte do olho pela linha dos olhos e testar CEW no treino.
- Avaliar no DMD, se fizer sentido.
- Medir o custo direto do filtro nas 5 sementes e levar o teste de alinhamento para o notebook.
- Corrigir a linha 380 de `docs/pesquisa_wakely.md`: só 2 dos 5 motoristas de validação e teste se repetem.
- Resolver a divergência da licença do NITYMED entre Kaggle (CC BY-ND 4.0) e DataPort (CC BY 4.0).
