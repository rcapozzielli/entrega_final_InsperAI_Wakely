# Wakely

Protótipo acadêmico da Insper AI que detecta sonolência ao volante com câmera e deep learning. **Não é um dispositivo de segurança e nunca deve ser testado dirigindo.**

Este arquivo resume o estado do projeto em 07/11/2026, depois das seções 8.5 a 8.7 (entrada rica, análise de erros e MIL com validação externa no DROZY, branch `feat/modelo-temporal`). A pesquisa completa está em `docs/pesquisa_wakely.md`, e o código e os resultados, em `wakely.ipynb`.

Prazos: apresentação intermediária em 12/11/2026, entrega final (notebook e paper) em 17/11/2026 e apresentação final em 18/11/2026.

## Como rodar

```bash
uv sync
uv run jupyter nbconvert --to notebook --execute --inplace wakely.ipynb --ExecutePreprocessor.timeout=-1
```

- Com o cache pronto (incluindo `rldd_rico/`, `rldd_rico_temporal/`, `drozy_rico/`, `rldd_mil/` e `drozy_mil/`), a pasta `len60` e o DROZY baixados, a execução leva cerca de 17 minutos em uma RTX 3050.
- Sem cache, leva cerca de 1 hora, com download de cerca de 1,7 GB, extração com o MediaPipe e 11 treinos.
- `data/` fica fora do Git. Ela guarda os dados, `data/cache/` (sinais e recortes) e `data/modelos/` (pesos).
- Para refazer a extração do FL3D, é preciso apagar os arquivos `fl3d_*` de `data/cache/`.
- A seção 8 baixa a pasta `len60` do UTA-RLDD (1,2 GB) e extrai os sinais em cerca de 2,5 h na CPU de um Apple M5, com cache por pessoa em `data/cache/rldd/`. Como as pessoas são independentes, a extração foi rodada em 4 processos com `extrair_pessoa`. As previsões da GRU e da TCN ficam em `data/cache/rldd_temporal/`. Apague essas pastas para refazer.
- A seção 8.5 refaz a extração com pose da cabeça e os 52 blendshapes em `data/cache/rldd_rico/` (160 MB). Ela levou cerca de 45 min em 4 processos numa RTX 3050 e leva cerca de 2 h num processo só. Mais de 4 processos estouram os 6 GB da GPU. As previsões das redes da seção 8.5 ficam em `data/cache/rldd_rico_temporal/`.
- A seção 8.7 baixa o DROZY (2,5 GB, ORBi) para `data/drozy/` e extrai os sinais em `data/cache/drozy_rico/`, o que levou 20 min em 4 processos (cerca de 1 h num só). As previsões ficam em `data/cache/rldd_mil/` (parte A) e `data/cache/drozy_mil/` (parte B). O treino das redes MIL leva segundos por semente.

## Pipeline atual

Webcam → MediaPipe → P(olho fechado) ou EAR → filtro de bocejo → regra de tempo → alerta.

- **Regra de alerta:** olho fechado por T = 1 s, o limite inferior da faixa de microssono do Euro NCAP. Há também os níveis de 3 s (sono) e 6 s (sem resposta), ainda pouco testados.
- **Filtro de bocejo:** ignora o olho fechado durante um bocejo detectado pela abertura da boca. Usa só frames passados, para valer também ao vivo.
- **Piso de 3 s (proposto):** olho fechado por 3 s ou mais dispara o aviso forte mesmo durante bocejo, para não silenciar quem dorme de boca aberta. Foi testado na seção 7 (custa 2 alarmes com o YOLO nos 44 vídeos), mas ainda não entrou na regra das seções 2 a 6.
- **Agente de RL (seção 7):** é um experimento. Ele não supera a regra e não faz parte do pipeline.
- **Modelo temporal (seção 8):** GRU, TCN e transformer sobre 1 minuto de sinais, no UTA-RLDD, também com cabeça e expressões (8.5). Nenhum supera o PERCLOS do minuto.
- **Rede MIL (seção 8.7):** cada vídeo é normalizado pelo seu 1º minuto, e o vídeo vira um saco de minutos com atenção. Ela supera a logística com os mesmos sinais no UTA e no DROZY. A demo mostra lado a lado a MIL, com calibração no 1º minuto de uso, e o PERCLOS do último minuto.
- **`demo/sonolencia.py`:** módulo da demo, sem depender do notebook.
  - `ExtratorRosto` dá a mesma linha de 61 sinais da extração da seção 8.5 (conferido num clipe do UTA: diferença máxima de 0,001 no P(fechado) e zero no resto).
  - `MonitorSonolencia` reamostra para 10 fps, calibra no 1º minuto e, a cada minuto completo, dá o PERCLOS e a P(sonolento) da MIL (média das 5 sementes, saco com os últimos 9 minutos). No DROZY, reproduz as previsões da parte B.
  - Os pesos ficam em `data/modelos/mil_gru4_uta.pt` (148 KB, fora do Git), gravados pela última célula da seção 8.7.
- **Demo com webcam (`demo/app.py`, 08/11/2026):** webcam do notebook → `ExtratorRosto` → regra de `demo/alerta.py` (YOLO, T = 1 s, filtro de bocejo, piso de 3 s e 6 s) + `MonitorSonolencia` (PERCLOS e MIL) → máquina de estados → painel no navegador (`demo/painel.html`, em http://localhost:8765), com o rosto espelhado, sons e as teclas F (alarme falso, só registra) e R (recalibrar). Rode da raiz do repositório: `uv run python demo/app.py` (`--camera 1` para outra câmera, `--video arquivo.mp4` para testar com vídeo, `--log eventos.csv` para registrar só os eventos). A regra ao vivo repete a do notebook nos 44 vídeos do FL3D (163 de 163 avisos de microssono, 12 de 12 do piso). Os tempos da máquina de estados (10 s sem rosto, 60 s de histerese, 5 min entre avisos de sonolência) são escolhas da demo e não foram validados. A demo ainda usa só o YOLO, sem a fusão da seção 6.3.

## Estrutura do notebook

| Seção | Conteúdo |
| --- | --- |
| 1 | Configuração e dados: MRL Eye, FL3D |
| 2 | Linha de base: MediaPipe, EAR, regra de alerta e varredura de T |
| 3 | MobileNetV3-Small no MRL Eye, com divisão por pessoa |
| 4 | CNN no vídeo e ajustes do sinal (4.2), com validação cruzada |
| 5 | Comparação entre MobileNetV3 e YOLO26n-cls, com 5 sementes |
| 6 | Falsos alarmes: filtro de bocejo (6.1), piscadas via NITYMED (6.2) e fusão do EAR com o YOLO (6.3) |
| 7 | Agente de RL no alerta: Q-learning com tabela, curva por λ, tecla "foi alarme falso" e mapa da política |
| 8 | Modelo temporal no UTA-RLDD: extração (8.1), análise inicial e falsos alarmes (8.2), PERCLOS e logística (8.3), GRU e TCN (8.4), cabeça, expressões e transformer (8.5), análise de erros (8.6), MIL com normalização pelo 1º minuto e validação externa no DROZY (8.7) |
| 9 | Resumo e próximos passos |

Funções principais: `fechamento`, `bocejo_ativo`, `alertas` e `avaliar_eventos` (seção 2), `treinar` e `prever` (seção 3), `contagens` e `deixar_um_video_de_fora` (seção 4.2), `rodar_agente`, `rodar_regra` e `treinar_agente` (seção 7), `extrair_pessoa`, `atributos`, `avisos_regra`, `metricas_8` e `prever_temporal` (seção 8), `extrair_pessoa_rico`, `carregar_rico`, `treinar_85`, `prever_85` e `auc_dentro_da_pessoa` (seções 8.5 e 8.6), `normalizar_videos`, `MILSono`, `treinar_87`, `prever_87`, `extrair_drozy` e `prever_b` (seção 8.7). A última célula da seção 8.7 grava os pesos da MIL para a demo.

As saídas gravadas vêm de uma execução completa na RTX 3050 do Rafael, em 07/11/2026, que incluiu as seções 8.5 a 8.7. As seções 1 a 6 reproduziram as saídas originais, e a seção 7 mudou nos números do YOLO (veja Resultados). A seção 8 usa os caches `rldd/` e `rldd_temporal/` gerados pela Luana na CPU de um Apple M5, com os pesos do YOLO da semente 42 do Rafael. Isso foi conferido em 2 clipes: o P(fechado) do cache tem correlação de 0,99 com essa semente, contra 0,72 a 0,87 com as sementes 1 e 2. A diferença que sobra deve vir do MediaPipe em Mac e em Windows, então uma extração nova deve ser feita toda numa máquina só. Numa execução completa no M5, as seções 3 a 6 mudaram um pouco (por exemplo, os falsos alarmes do YOLO com filtro foram de 10,2 para 9,4), porque CPU e GPU arredondam as contas de forma diferente.

## Dados

| Base | Uso |
| --- | --- |
| MRL Eye | Treinar os classificadores de olho. Infravermelho, 37 pessoas |
| FL3D | Avaliar em vídeo, com rótulo por frame. 44 vídeos, sem piscadas. Os 5 vídeos de holdout são o teste, e os outros 39, a calibração |
| NITYMED | Vídeos originais do FL3D, usados para recolocar os frames removidos |
| UTA-RLDD recortado | Seção 8: só a pasta `len60`, com 1.136 clipes de 1 min a 10 fps, de 60 pessoas, alertas ou sonolentas (falta a sonolenta da pessoa 42). Os clipes de cada vídeo são minutos seguidos, e os 10 com menos de 600 frames são o último de cada vídeo |
| DROZY | Seção 8.7, validação externa: 14 pessoas, 36 testes de reação de 10 min com privação de sono crescente (descansado, ~18 h e ~28 h acordado), câmera infravermelha. Rótulo: KSS ≥ 7. Licença só para pesquisa, sem redistribuir e sem mostrar as imagens; citar Massoz et al., WACV 2016 |

## Decisões

- **T = 1 s fixo.** T = 0,4 s vencia só porque o FL3D não tem piscadas. Ele fica apenas na varredura, como referência otimista.
- **Filtro de bocejo (opção 2, escolhida pelo grupo):** ignorar o olho fechado durante o bocejo, em vez de só reportar à parte, exigir mais tempo ou dar um aviso mais leve.
- **Repositório público e licença AGPL-3.0,** o que atende à exigência da `ultralytics`.
- **Figuras com recortes de olhos ficam no notebook,** para mostrar os dados, com as fontes citadas.
- **Não treinar CNN do zero.** Os classificadores usam fine-tuning a partir do ImageNet. Do zero, só o modelo temporal.
- **YOLO detector e SAM 2 estão fora do pipeline.** A pergunta sobre isso à organização ainda está em aberto.
- **Agente de RL fica como experimento.** A demo usa a regra (YOLO, T = 1 s, filtro de bocejo), e a sugestão é somar o piso de 3 s.
- **Modelo temporal:** janela de 60 s, entradas P(fechado), EAR, boca e rosto, e YOLO da semente 42. Os atributos da seção 8.2 e os hiperparâmetros da GRU e da TCN foram fixados antes de ver os resultados e não devem ser ajustados olhando as dobras de teste.
- **Linha de base por pessoa:** não dá para avaliar no UTA-RLDD (seção 8.6), porque cada classe foi gravada num dia. Fica para uma base com os dois estados na mesma sessão ou para as gravações do grupo, só como teste.
- **Seção 8.5 com protocolo fixado antes** (`docs/protocolo_8_5.md`, aprovado em 07/11/2026). Canais, atributos, modelos e hiperparâmetros não mudam olhando as dobras de teste. Qualquer teste novo nessa base entra como exploratório.
- **A seção 8.6 é exploratória.** Ela usa previsões de teste e não pode orientar ajustes nos modelos das seções 8.3 a 8.5.
- **Seção 8.7 com protocolo fixado antes** (`docs/protocolo_8_7.md`, aprovado em 07/11/2026, antes de treinar e de extrair o DROZY). A rede principal é a MIL-GRU-4 híbrida, e a linha de base principal, a Logística-Δ16. O critério é IC acima de zero no UTA e diferença positiva no DROZY. O DROZY é só teste: nada é treinado, calibrado ou escolhido nele. O MIL-Transformer, que foi o melhor, era secundário, e só um teste novo pode confirmá-lo.

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
- **Fusão EAR + YOLO (seção 6.3, protocolo fixado antes de rodar, 08/11/2026):** a média dos dois sinais, com filtro, acha 90,7% dos episódios de 1 s ou mais (149,6 de 165) com 6,0 falsos alarmes. Ganha do YOLO em acertos (+3,9 pontos, de +0,8 a +7,7) e do EAR em falsos alarmes (−10, de −21 a −1,2). O mínimo dos dois corta falsos alarmes (5,6), mas não acha mais. No holdout, com o limiar escolhido na calibração (0,35 na semente 42), a média empata com o YOLO (12,4 de 14, 0,6 falso alarme). A ideia veio de olhar as seções 5 e 6, nos mesmos 44 vídeos, então o ganho pode ser um pouco otimista.
- **Piscadas (YOLO, semente 42, com filtro, 46 min):** 8 alarmes atravessam os 710 buracos de até 0,5 s, cerca de 1%. No total são 27 alarmes, dos quais 17 estão em buracos longos sem rótulo.
- **Falsos alarmes em pessoas acordadas (seção 8.2, UTA-RLDD, 9,5 h, regra da demo a 10 fps):** 6,7 por hora (IC95% de 0,7 a 16). 54 das 60 pessoas não têm nenhum, uma pessoa dá 40 dos 64, e as 5 com mais alarmes somam 97%. As 3 primeiras têm EAR de olho aberto de 0,19 a 0,20, contra 0,25 da mediana. Na classe sonolenta, são 63 alarmes por hora.
- **Sonolência em 1 minuto (seção 8, 5 dobras por pessoa, 1.126 clipes):** PERCLOS com limiar AUC 0,774; regressão logística 0,746; GRU 0,750 ± 0,009; TCN 0,754 ± 0,014 (5 sementes). Nenhuma diferença é conclusiva (GRU - PERCLOS: -0,024, de -0,059 a +0,012). Por vídeo, a GRU acerta 74,6%, e o PERCLOS, 65,5%. O artigo da base fez 65,2% por vídeo, com 3 classes e outro protocolo.
- **Entrada rica (seção 8.5, extração nova, mesmas dobras):** PERCLOS 0,775; Logística-6 0,744; Logística-16, com cabeça e expressões, 0,772; GRU-4 0,752; GRU-14 híbrida 0,729; TCN-14 híbrida 0,736; transformer 0,754 (5 sementes). Contra a Logística-16, a GRU-14 (-0,044, de -0,072 a -0,017) e a TCN-14 (-0,036, de -0,067 a -0,004) são piores de forma conclusiva, e o transformer empata (-0,018, de -0,046 a +0,009). Os sinais novos ajudam a logística sem certeza (+0,028, de -0,010 a +0,064). O controle de pose média dá 0,506. As redes de 14 canais sobreajustam cedo (melhor época mediana de 2 a 9, contra 15 na GRU-4).
- **Análise de erros (seção 8.6, exploratória):** AUC dentro da pessoa de 0,82 a 0,85, contra 0,74 a 0,78 entre pessoas. O PERCLOS sobe 0,032 do alerta ao sonolento na mesma pessoa e varia 0,027 entre pessoas alertas. Acerto nos alertas de 38% no terço com olho menor na imagem e nos sonolentos de 39% no terço com olho maior. Acerto nos sonolentos de 54% no 1º minuto e 74% do 8º em diante. Os 9 modelos concordam (Spearman 0,82), e 17 dos 119 vídeos são errados por todos. Dentro da pessoa, a pose média separa as classes com 0,83 a 0,86 (sem direção; acaso 0,61), quase como o PERCLOS (0,89).
- **MIL normalizada pelo 1º minuto (seção 8.7, AUC por vídeo, 5 sementes):**
  - **UTA, 118 vídeos:**
    - MIL-GRU-4 0,742, contra 0,654 da Logística-Δ16 (+0,089, de +0,007 a +0,181);
    - MIL-Transformer-14 0,875;
    - GRU-4 com média 0,737 (a atenção não muda nada);
    - PERCLOS absoluto 0,814, e o ΔPERCLOS fica 0,207 abaixo dele: a normalização custa caro;
    - controle de pose 0,510.
  - **DROZY, 36 vídeos, sem ajuste:**
    - MIL-GRU-4 0,708, contra 0,575 da Logística-Δ16 (+0,133, de -0,034 a +0,278);
    - MIL-Transformer 0,743;
    - PERCLOS absoluto 0,619, e 0,511 com a mesma iluminação;
    - controle de pose 0,641, então os resultados devem ser lidos com cautela.
  - **Extração no DROZY:** o rosto foi achado em 99,8% dos frames.
  - **Checagem de vazamento:** com os rótulos embaralhados dentro da pessoa, a AUC fica entre 0,49 e 0,61.

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
- **Sessão de gravação no UTA-RLDD:** dentro de cada pessoa, sinais que só refletem a câmera do dia separam as classes. Qualquer comparação dentro da pessoa nessa base mistura sono e sessão.
- **DROZY:** nunca mostrar frames, nem no notebook, nem no paper, nem nos slides, e não versionar nada da base. O rosto é pequeno (olho de ~10 px), então a extração usa rastreio em modo de vídeo e um recorte ampliado. A luz foi apagada nos testes 2 e 3, e os testes 2 e 3 das pessoas 1 a 8 estão a ~15 fps.
- **Viés do limiar único:** os falsos alarmes em pessoas acordadas se concentram em quem tem o olho aberto menor na imagem, seja pela anatomia, pelo ângulo da câmera ou pelo olhar.
- **Reprodutibilidade:** o teste de alinhamento com o NITYMED (264 amostras), a inspeção visual dos recortes, a checagem de continuidade dos clipes do UTA-RLDD e a olhada nos frames das pessoas com mais alarmes foram feitos fora do notebook. Ele só registra as conclusões.

## Convenções

- Não versionar dados, vídeos, recortes soltos, caches nem pesos. O `.gitignore` já cobre isso.
- Não versionar segredos. O repositório é público.
- Trabalhar em branch com PR. Conflitos em `.ipynb` são difíceis de resolver, então avise o grupo antes de editar o notebook.
- Depois de mudar código no notebook, executar tudo e conferir se os números do texto, do resumo (seção 9) e do `README.md` batem com as saídas.
- Gravações do grupo só em local seguro, na mesa ou em carro desligado e parado, e depois de consultar o orientador sobre LGPD e ética.

## Próximos passos

1. **Deep learning na sonolência, depois da seção 8.7:** a MIL normalizada pelo 1º minuto entra na demo, ao lado do PERCLOS (`demo/sonolencia.py`). Falta:
   - testar a MIL-Transformer, que foi a melhor, num protocolo novo;
   - atacar o custo da normalização, que tira o sono de quem já começa sonolento.
2. **Demo com webcam (para 12/11): feita** (`demo/app.py`). Falta medir FPS na máquina da apresentação (12 a 19 quadros/s na webcam de uma RTX 4060) e ensaiar com pelo menos 2 minutos de câmera, para a MIL aparecer. O aviso de sonolência usa o `MonitorSonolencia` de `demo/sonolencia.py` (MIL e PERCLOS), e o `ExtratorRosto` também entrega o P(fechado) e a boca da regra, com um MediaPipe só por quadro. A webcam precisa de pelo menos 10 fps.
3. **Fusão na demo:** trocar o P(fechado) do YOLO pela média com o EAR (limiar 0,35, referência do EAR no começo do uso) e confirmar a fusão numa base com microssonos marcados além do FL3D.
4. **Falsos alarmes em situações difíceis:** gravações encenadas do grupo, só como teste, com conversa, olhares para baixo e bocejos com olho fechado, incluindo microssono encenado junto de bocejo.
5. **Piso de 3 s na regra principal:** levar o piso da seção 7 para a seção 6 e conferir os números.
6. **Linha de base por pessoa (próxima etapa):** começo do uso como referência, contra o viés do olho pequeno. Avaliar fora do UTA-RLDD (seção 8.6).

## Pontos fracos atuais

- **Sonolência antes do microssono:** no UTA, o PERCLOS absoluto ainda é o melhor sinal simples (0,77 por minuto e 0,81 por vídeo). O rótulo do UTA-RLDD é autorrelatado, vale para o vídeo inteiro e mistura o sono com o dia da gravação.
- **Deep learning na sonolência ainda frágil:** a MIL supera a logística com os mesmos sinais no UTA e no DROZY, mas não o PERCLOS absoluto no UTA. O DROZY tem só 14 pessoas, e a iluminação também muda entre os testes. A atenção não acrescenta nada à média simples dos minutos.
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
