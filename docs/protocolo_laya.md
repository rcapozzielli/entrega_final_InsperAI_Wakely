# Protocolo: Laya como "cérebro de decisão"

Escrito em 13/11/2026 pelo Antônio, **antes de rodar o Laya em qualquer dado e antes de ver qualquer resultado das bases novas**. Segue as regras da seção 10 do notebook: o protocolo não muda depois de ver o resultado, números finais vêm só de dados reais, e qualquer conta fora daqui entra como exploratória.

## A pergunta

Hoje o Wakely decide o estado do motorista com regras escritas à mão (T = 1 s, filtro de bocejo, piso de 3 s, máquina de estados da demo). A pergunta é:

> Um modelo de decisão aberto, o **Laya** (ConvAI Innovations, Apache 2.0, `convaiinnovations/laya`), que lê um resumo em JSON dos últimos segundos, decide melhor que as regras e que uma regressão logística com o mesmo resumo?

O Laya não vê imagem. Ele recebe só os sinais que o Wakely já calcula. Por isso, ele não substitui o YOLO, o EAR nem o MediaPipe: ele só troca a camada de decisão.

## O que o Laya recebe

Uma **janela de 2 s**, deslizando a cada 0,5 s, vira este JSON (campos fixados aqui, nenhum é acrescentado depois):

| Campo | De onde vem |
|---|---|
| `p_fechado_media`, `p_fechado_max` | P(fechado) do YOLO, média dos dois olhos |
| `fechado_max_s` | Maior trecho seguido com P(fechado) ≥ 0,4 na janela e antes dela (até 8 s para trás), em segundos |
| `ear_rel_media`, `ear_rel_min` | EAR ÷ referência da pessoa (mediana dos primeiros 30 s), como na fusão da seção 6.3 |
| `boca_max`, `bocejo` | Abertura da boca e o filtro de bocejo da demo (0,25, 3 quadros, 1 s de margem) |
| `cabeca_pitch_media`, `cabeca_pitch_min`, `cabeca_yaw_abs_max` | Pose da cabeça do MediaPipe, em graus, menos a mediana dos primeiros 30 s |
| `olhar_baixo_media` | Média dos blendshapes `eyeLookDownLeft` e `eyeLookDownRight` |
| `rosto_frac` | Fração dos quadros com rosto achado |

Só quadros **passados** entram, para valer ao vivo.

## As perguntas feitas ao Laya

1. **Escolha** (`estado`): `normal`, `distraido` (olhando para baixo ou para o lado, sem estar de olho fechado), `microssono` (olho fechado por 1 s ou mais).
2. **Sim ou não** (`alarme`): disparar o alarme de microssono agora?

A sonolência de minutos fica de fora deste protocolo: ela já tem o PERCLOS e a MIL, e o critério dela está na seção 10.4.

## Dados e papéis

Os papéis seguem a tabela da seção 10.3. A base que treina não é a que dá o número final.

| Base | Papel aqui | Rótulo da janela |
|---|---|---|
| Gravações do Antônio (4 vídeos) | **Só explorar e testar o código.** Nenhum número delas vai para o paper como resultado | Pelos trechos rotulados (ESPAÇO e revisão) |
| FL3D, 39 vídeos de calibração | **Treinar** a parte de microssono | `microssono` se a janela termina dentro de um episódio de 1 s ou mais; `normal` caso contrário (bocejo entra como `normal`) |
| Drive&Act, motoristas de treino | **Treinar** a parte de distração | `distraido` nas atividades de celular, pegar objeto e olhar para outro lugar; `normal` em dirigir; as demais ficam fora. A lista exata de atividades é fixada ao abrir as anotações, **antes** de extrair qualquer sinal, e anotada neste arquivo |
| FL3D, 5 vídeos de holdout | Confirmação fraca de microssono | Como acima |
| BINUS (47 vídeos de teste) | **Teste** de microssono e falso alarme | Fechamento de 1 s ou mais vira `microssono` |
| Drive&Act, motoristas de teste | **Teste** de distração | Como acima |
| Eyeblink8 | **Teste** de falso alarme em piscadas | Tudo `normal` |

A divisão de treino e teste do Drive&Act é a dos próprios autores (por motorista). Se uma base não estiver disponível até 15/11, o teste vale com as que estiverem, e isso é registrado.

### Atividades do Drive&Act (fixadas em 13/11, ao abrir as anotações)

Arquivo usado: `activities_3s/a_column_driver/midlevel.chunks_90.csv` (39 atividades, 10.333 trechos de até 3 s, com início e fim em quadros). A extração dos sinais já tinha começado nesse momento, mas nenhuma janela, rótulo ou estatística por atividade tinha sido calculada.

- **`distraido`:** `interacting_with_phone`, `reading_magazine`, `reading_newspaper`, `working_on_laptop`, `writing`, `using_multimedia_display`, `fetching_an_object`, `placing_an_object`, `looking_or_moving_around (e.g. searching)`, `looking_back_left_shoulder`, `looking_back_right_shoulder`.
- **`normal`:** `sitting_still`.
- **Fora:** as outras 27 atividades (comer, beber, vestir casaco, entrar e sair do carro, falar ao telefone e outras), porque não são claramente nem "olhando para a frente" nem "olhando para baixo ou para o lado".
- **Divisão:** a `split_0` dos autores (treino, validação e teste por participante). A validação entra no treino; o teste fica só para o teste.
- **Observação:** no Drive&Act o carro está em modo autônomo em parte do tempo, então ler, usar o notebook e o celular são atividades esperadas. Isso não muda nada aqui: o que importa é se o olho e a cabeça parecem de alguém distraído.

## O que é comparado

Todos recebem as **mesmas janelas** e são treinados nos **mesmos dados**:

1. **Regra atual:** YOLO com filtro de bocejo e T = 1 s (microssono), mais uma regra simples de distração fixada aqui: `cabeca_pitch_media` 15° ou mais abaixo da referência por 2 s.
2. **Regressão logística** multinomial sobre os mesmos campos do JSON (padronizados com média e desvio do treino).
3. **Laya, só com camadas pequenas** (o modo `agent.fit` da biblioteca, sem mexer nos pesos do modelo).
4. **Laya com fine-tuning**, se couber nos 8 GB da RTX 4060 (micro-lote 1, acumulação de 32, 4 épocas, os padrões do repositório). Se não couber, isso é registrado e só o item 3 vale.

Nada é ajustado olhando o teste: os hiperparâmetros acima são os únicos. Cada modelo treinável roda com as sementes **0, 1 e 2**, e o resultado é a média.

## Métricas e critério

- **Microssono:** as definições da frente B (`docs/protocolo_metricas_f.md`): recall nos episódios de 1 s ou mais, precisão por alarme, F1 e **F2**, com um alarme por trecho e tolerância de 0,5 s.
- **Distração:** F1 da classe `distraido` por janela.
- **Falso alarme:** alarmes de microssono por hora nas bases sem microssono (Eyeblink8 e as janelas `normal` e `distraido` do Drive&Act).
- **Incerteza:** bootstrap pareado por vídeo (ou por motorista), 5.000 sorteios, IC95% pelos percentis 2,5 e 97,5, como no notebook.

**O Laya só conta como melhor** se, nas bases de **teste**, valerem as três condições:
1. F2 de microssono maior que o da regra atual, com IC95% da diferença sem zero.
2. Alarmes falsos por hora não maiores que os da regra atual (somando as bases de teste pelo tempo, como na 10.4).
3. Melhor que a regressão logística com os mesmos campos, com IC95% sem zero.

Se a condição 3 falhar, a conclusão é que o ganho vem dos campos do JSON, e não do Laya. Se nenhuma condição valer, o Laya fica como trabalho futuro, com o resultado reportado igual.

## Riscos conhecidos

- **Bases diferentes, câmeras diferentes:** o FL3D é RGB à noite e o Drive&Act é infravermelho. O modelo pode aprender "qual base é" em vez de "qual estado". Por isso o teste é em pessoas e bases que o modelo não viu, e a regressão logística passa pelo mesmo problema.
- **Microssonos encenados** no FL3D, na BINUS e nas gravações.
- **Poucos episódios** de microssono no teste: os intervalos devem sair largos.
- **O Laya foi feito para texto** (e-mails, chamados). Nada garante que ele entenda números; isso é parte do que este teste mede.

## Detalhes de implementação (fixados em 13/11, antes de qualquer previsão nas janelas de teste)

- **Perguntas em inglês,** porque o checkpoint base (`convaiinnovations/laya`, raiz, em inglês) foi treinado assim. O texto está em `experimentos/perguntas_laya.py`.
- **De janela para alarme:** cada janela classificada como `microssono` liga o alarme; janelas `microssono` seguidas contam como **um só alarme**, no fim da primeira janela. Os acertos e os falsos alarmes saem dessas horas com as definições da frente B (tolerância de 0,5 s, episódios de 1 s ou mais). A regra atual é medida do jeito de sempre, quadro a quadro (`demo/alerta.py`).
- **Janelas de teste:** BINUS (microssono pelos mesmos episódios do `protocolo_testes_bases_novas.md`), Eyeblink8 (tudo `normal`) e os motoristas de teste do Drive&Act.
- **Teste de sanidade sem treino (13/11):** o Laya roda na RTX 4060 (2,5 GB) e, sem treino, dá probabilidades quase iguais às três classes em 4 janelas do treino do FL3D, como o autor avisa para o checkpoint base. Nada foi escolhido a partir disso.

## Mudança em 13/11, antes de treinar: só microssono

O Drive&Act saiu dos testes (o MediaPipe achou o rosto em 1% a 28% dos quadros; ver `docs/protocolo_testes_bases_novas.md`), e era a única base de treino de `distraido`. Por isso, **antes de treinar qualquer modelo**, o teste do Laya ficou só com o microssono:
- **Treino:** as 4.778 janelas dos 39 vídeos de calibração do FL3D (`normal` ou `microssono`).
- **Teste:** BINUS (microssono e falso alarme), Eyeblink8 (falso alarme) e o holdout do FL3D (confirmação fraca).
- A pergunta continua a mesma; como não há exemplo de `distraido` no treino, o fine-tuning só aprende as duas classes que existem.
- O critério continua o mesmo, sem a parte de distração: F2 de microssono e alarmes por hora contra a regra atual e contra a logística.

## O que fica fora

- Mudar campos, janela, limiar de 0,4, regra de distração ou hiperparâmetros depois de ver qualquer resultado de teste.
- Usar as gravações do Antônio para escolher qualquer coisa que entre no número final.
- Sonolência de minutos (fica com o PERCLOS e a MIL, seção 10.4).

## Avaliação (escrita em 14/11, antes de qualquer previsão do Laya nas janelas de teste)

- **Sementes:** o primeiro treino da semente 0 foi interrompido na época 4 (o computador precisou ser desligado). Ele foi descartado (`laya_ft_s0_interrompido`), e as três sementes foram treinadas de novo do zero, com a mesma configuração.
- **Classe de cada janela:** a de maior probabilidade. Na logística, que só viu `normal` e `microssono`, isso é P(microssono) > 0,5. No Laya, se a maior for `distraido`, a janela não liga o alarme.
- **Episódios verdadeiros:** os mesmos dos outros protocolos. Na BINUS, os de `testes_bases_novas.py`; no FL3D, os quadros `microsleep` com buracos de até 0,5 s juntados, como em `construir_janelas.py`. Acerto e falso alarme seguem a frente B (0,5 s de tolerância; falso = alarme longe de qualquer episódio anotado, de qualquer duração).
- **Laya:** as métricas de cada semente são calculadas separadas, e a média das três é o número do Laya, também dentro de cada sorteio do bootstrap.
- **Bases da condição 2:** só o Eyeblink8 (o Drive&Act saiu, e o UTA não faz parte deste protocolo). Os falsos alarmes da BINUS são mostrados à parte.
- **Conferência do código:** a regra atual medida por esta avaliação deu os mesmos números de `testes_bases_novas.py` (BINUS 48 e 44 achados; Eyeblink8 10,6 e 18,2 por hora). Em 14/11, a referência do EAR da fusão foi corrigida para o percentil 75 (ver `docs/protocolo_testes_bases_novas.md`); com isso, a fusão dá 46 achados na BINUS, e os números do Laya não mudam. Os campos `ear_rel_*` do Laya continuam com a mediana, como este protocolo definiu.
- **Mudança em 14/11, 1h45, antes de qualquer previsão do Laya:** cada semente levou cerca de 2h20 nesta máquina, e o grupo decidiu, por tempo, **ficar só com a semente 0**. As sementes 1 e 2 não foram treinadas. O resultado do Laya é de uma semente só e não mostra a variação entre sementes; isso entra como limitação.

## Segunda tentativa: Laya com espera de 1 s (escrita em 14/11, antes de rodar)

**Por que existe:** o Laya da semente 0 passou nas condições 1 e 3, mas falhou na 2 (34,8 alarmes falsos por hora no Eyeblink8, contra 10,6 da regra). Ele dispara com uma janela só, enquanto a regra atual espera o olho ficar fechado por T = 1 s. **Esta tentativa foi pensada depois de ver esse resultado**, então a BINUS, o Eyeblink8 e o holdout do FL3D já não servem para confirmar nada: eles aparecem só como **exploratórios**.

**A única mudança, fixada antes de rodar:** o alarme só dispara quando há **2 janelas seguidas** classificadas como `microssono`, o que dá 1 s com o passo de 0,5 s. O valor 2 vem do T = 1 s da regra do notebook, e **não foi escolhido testando valores**; nenhum outro valor (3, 4, limiares de probabilidade) será testado. O alarme cai no fim da segunda janela, e janelas `microssono` seguidas continuam valendo um alarme só. O mesmo vale para a logística, para a comparação ser justa. O modelo do Laya não muda (o mesmo fine-tuning da semente 0, sem treinar de novo).

**Teste confirmatório (base que nenhum modelo de janela viu):** a classe alerta do **UTA-RLDD** (60 pessoas, 9,5 h, 10 quadros por segundo, os mesmos sinais em cache da seção 3), em que todo alarme é falso. As janelas são montadas do mesmo jeito (`janelas.py`), com os trechos de cada pessoa juntados na ordem dos minutos, como em `testes_bases_novas.py`.

**Critério:** o Laya com espera passa na condição 2 se der **não mais alarmes falsos por hora que a regra atual (YOLO com filtro, 6,3 por hora) no UTA alerta**, e o intervalo (bootstrap pareado por pessoa, 5.000 sorteios) é reportado. Como não sobrou nenhuma base de microssono nunca vista, o F2 da BINUS com espera é só exploratório. **Mesmo que passe, o Laya não vira o sistema do Wakely por esta tentativa**: o resultado vira uma recomendação para testar em uma base de microssono nova.
