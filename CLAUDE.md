# Wakely

Protótipo acadêmico da Insper AI que detecta sonolência ao volante com câmera e deep learning. **Não é um dispositivo de segurança e nunca deve ser testado dirigindo.**

Este arquivo resume o estado do projeto em 05/11/2026, depois do PR #10 (agente de RL). A pesquisa completa está em `docs/pesquisa_wakely.md`, e o código e os resultados, em `wakely.ipynb`.

Prazos: apresentação intermediária em 12/11/2026, entrega final (notebook e paper) em 17/11/2026 e apresentação final em 18/11/2026.

## Como rodar

```bash
uv sync
uv run jupyter nbconvert --to notebook --execute --inplace wakely.ipynb --ExecutePreprocessor.timeout=-1
```

- Com o cache pronto, a execução leva cerca de 4 minutos em uma RTX 3050.
- Sem cache, leva cerca de 1 hora, com download de cerca de 1,7 GB, extração com o MediaPipe e 11 treinos.
- `data/` fica fora do Git. Ela guarda os dados, `data/cache/` (sinais e recortes) e `data/modelos/` (pesos).
- Para refazer a extração do FL3D, é preciso apagar os arquivos `fl3d_*` de `data/cache/`.

## Pipeline atual

Webcam → MediaPipe → P(olho fechado) ou EAR → filtro de bocejo → regra de tempo → alerta.

- **Regra de alerta:** olho fechado por T = 1 s, o limite inferior da faixa de microssono do Euro NCAP. Há também os níveis de 3 s (sono) e 6 s (sem resposta), ainda pouco testados.
- **Filtro de bocejo:** ignora o olho fechado durante um bocejo detectado pela abertura da boca. Usa só frames passados, para valer também ao vivo.
- **Piso de 3 s (proposto):** olho fechado por 3 s ou mais dispara o aviso forte mesmo durante bocejo, para não silenciar quem dorme de boca aberta. Foi testado na seção 7 (custa 2 alarmes com o YOLO nos 44 vídeos), mas ainda não entrou na regra das seções 2 a 6.
- **Agente de RL (seção 7):** é um experimento. Ele não supera a regra e não faz parte do pipeline.
- **Ainda não existe:** o modelo temporal (GRU ou TCN) para sonolência em janelas longas, e a demo com webcam.

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
| 8 | Resumo e próximos passos |

Funções principais: `fechamento`, `bocejo_ativo`, `alertas` e `avaliar_eventos` (seção 2), `treinar` e `prever` (seção 3), `contagens` e `deixar_um_video_de_fora` (seção 4.2), `rodar_agente`, `rodar_regra` e `treinar_agente` (seção 7).

A seção 7 foi rodada numa RTX 4060 com os caches e pesos da `data/` do Rafael. As seções 1 a 6 mantêm as saídas originais, e a execução local reproduz esses números até a quarta casa decimal.

## Dados

| Base | Uso |
| --- | --- |
| MRL Eye | Treinar os classificadores de olho. Infravermelho, 37 pessoas |
| FL3D | Avaliar em vídeo, com rótulo por frame. 44 vídeos, sem piscadas. Os 5 vídeos de holdout são o teste, e os outros 39, a calibração |
| NITYMED | Vídeos originais do FL3D, usados para recolocar os frames removidos |
| UTA-RLDD recortado | Planejado para treinar a GRU ou TCN. Ainda não baixado |

## Decisões

- **T = 1 s fixo.** T = 0,4 s vencia só porque o FL3D não tem piscadas. Ele fica apenas na varredura, como referência otimista.
- **Filtro de bocejo (opção 2, escolhida pelo grupo):** ignorar o olho fechado durante o bocejo, em vez de só reportar à parte, exigir mais tempo ou dar um aviso mais leve.
- **Repositório público e licença AGPL-3.0,** o que atende à exigência da `ultralytics`.
- **Figuras com recortes de olhos ficam no notebook,** para mostrar os dados, com as fontes citadas.
- **Não treinar CNN do zero.** Os classificadores usam fine-tuning a partir do ImageNet. Do zero, só o modelo temporal.
- **YOLO detector e SAM 2 estão fora do pipeline.** A pergunta sobre isso à organização ainda está em aberto.
- **Agente de RL fica como experimento.** A demo usa a regra (YOLO, T = 1 s, filtro de bocejo), e a sugestão é somar o piso de 3 s.

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
- **Agente de RL (seção 7, linha do tempo completa, 11 dobras por vídeo, 5 sementes):** não supera a regra em nenhum λ. Com YOLO e λ = 10, acha 143 de 165 episódios de 1 s ou mais com 15,4 falsos alarmes (4,2 fortes), contra 149 e 10 da regra com piso. Aprende sozinho a ignorar o bocejo e avisa com 0,8 s quando já houve 3 ou mais fechamentos longos no último minuto. A tecla simulada tira de 6% a 22% dos falsos alarmes no mesmo λ.
- **Piso de 3 s ignorando o filtro de bocejo:** custa 2 alarmes com o YOLO e 22 com o EAR, nos 44 vídeos.
- **Piscadas (YOLO, semente 42, com filtro, 46 min):** 8 alarmes atravessam os 710 buracos de até 0,5 s, cerca de 1%. No total são 27 alarmes, dos quais 17 estão em buracos longos sem rótulo. **A taxa real de falso alarme ainda não está medida.**

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
- **Reprodutibilidade:** o teste de alinhamento com o NITYMED (264 amostras) e a inspeção visual dos recortes foram feitos fora do notebook. Ele só registra as conclusões.

## Convenções

- Não versionar dados, vídeos, recortes soltos, caches nem pesos. O `.gitignore` já cobre isso.
- Não versionar segredos. O repositório é público.
- Trabalhar em branch com PR. Conflitos em `.ipynb` são difíceis de resolver, então avise o grupo antes de editar o notebook.
- Depois de mudar código no notebook, executar tudo e conferir se os números do texto, do resumo (seção 8) e do `README.md` batem com as saídas.
- Gravações do grupo só em local seguro, na mesa ou em carro desligado e parado, e depois de consultar o orientador sobre LGPD e ética.

## Próximos passos

1. **Demo com webcam (para 12/11):** regra com YOLO, filtro de bocejo e piso de 3 s, FPS reais, estado "sem rosto visível" e os três níveis de alerta.
2. **Falsos alarmes reais:** medir em pessoas acordadas (classe alerta do UTA-RLDD) e em gravações encenadas do grupo, só como teste, com piscadas, conversa, olhares para baixo e bocejos com olho fechado, incluindo microssono encenado junto de bocejo.
3. **Modelo temporal:** linha de base com PERCLOS e GRU ou TCN sobre a série de P(fechado), treinada no UTA-RLDD recortado, com validação por pessoa. A GRU ou TCN precisa superar a linha de base.
4. **Piso de 3 s na regra principal:** levar o piso da seção 7 para as seções 6 e 8, e conferir os números.

## Pontos fracos atuais

- **Só o sinal tardio:** sem o modelo temporal, o sistema detecta o olho já fechado, e não a sonolência antes do microssono.
- **Teste pequeno:** o holdout tem 2 vídeos com microssono, e a validação cruzada é por vídeo, não por motorista.
- **Taxa real de falso alarme não medida:** o FL3D removeu as piscadas, e a maioria dos alarmes na linha do tempo completa cai em trechos sem rótulo.
- **Redes × EAR:** nenhum classificador supera o EAR de forma conclusiva. O treino é em infravermelho (MRL) e o teste em RGB.
- **Recorte do olho:** fica torto quando a cabeça cai, justamente no microssono.
- **Agente de RL:** tem poucos dados por pessoa (vídeos de 20 s a 2 min) para aprender a personalizar.

## Pendências menores

- `GroupKFold` no MRL: a divisão por pessoa ainda é uma só, e as sementes não medem a variação entre grupos de pessoas.
- MediaPipe separado por óculos, pouca luz e cabeça inclinada.
- Alinhar o recorte do olho pela linha dos olhos e testar CEW no treino.
- Avaliar no DMD, se fizer sentido.
- Medir o custo direto do filtro nas 5 sementes e levar o teste de alinhamento para o notebook.
- Atualizar o início do status e a descrição do notebook no `README.md`.
- Corrigir a linha 380 de `docs/pesquisa_wakely.md`: só 2 dos 5 motoristas de validação e teste se repetem.
- Resolver a divergência da licença do NITYMED entre Kaggle (CC BY-ND 4.0) e DataPort (CC BY 4.0).
