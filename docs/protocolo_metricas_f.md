# Protocolo da frente B: precisão por alarme, F1 e F2 no alerta de microssono

Escrito em 13/11/2026, **antes de calcular qualquer F2 ou qualquer intervalo de F1 e F2**, e aprovado pelo Rafael em 13/11/2026. O protocolo não muda depois disso. Qualquer conta fora dele entra no notebook marcada como exploratória.

## Por que este protocolo

Na apresentação intermediária (12/11), a banca pediu uma métrica que junte acerto e alarme falso. Hoje as tabelas das seções 2, 5, 6 e 6.3 mostram as duas coisas separadas: o recall nos episódios de 1 s ou mais e a contagem de falsos alarmes. Isso dificulta comparar, por exemplo, um sinal que acha mais microssonos mas alarma mais com outro que acha menos e alarma menos.

As métricas F resumem os dois lados num número só. O F1 pesa os dois igualmente. O F2 dá mais peso ao recall, porque, num alerta de sonolência, perder um microssono é pior do que dar um alarme falso.

**O que já se sabe antes deste protocolo:** os acertos e os falsos alarmes de todas as tabelas já foram vistos, e o F1 de evento já aparece na varredura de T (seção 2.3) e é o critério de escolha do limiar (seções 4.2 a 6.3). Os valores pontuais de F1 e F2 são uma conta direta dessas contagens. Por isso, o que este protocolo fixa antes de olhar é **a definição, o β, as tabelas, as comparações e o modo de medir a incerteza**, e não a ausência de qualquer informação sobre os números.

## Definições

Todas as contagens vêm de `avaliar_eventos` (seção 2.3) e, na validação cruzada, de `contagens` e `deixar_um_video_de_fora` (seção 4.2), **sem nenhuma mudança nessas funções**.

- **Episódio:** trecho seguido de frames `microsleep`, juntando buracos de até 0,5 s (seção 2.3). Só entram os **episódios de 1 s ou mais** (`dur_min = T_ALERTA`, colunas `ac_l` e `ep_l`), porque T = 1 s não pretende detectar episódios mais curtos.
- **Alarme:** disparado quando um trecho fechado chega a T = 1 s, uma vez por trecho.
- **Acerto:** episódio de 1 s ou mais com pelo menos um alarme dentro dele, com tolerância de 0,5 s antes do início e depois do fim. Cada episódio conta no máximo uma vez.
- **Falso alarme:** alarme que não cai dentro de nenhum episódio, de qualquer duração, com a mesma tolerância (coluna `falsos`). Continua separado em "em bocejo" e "fora de bocejo", como na seção 6.
- **Alarmes que não entram em nenhuma das duas contas:** um alarme dentro de um episódio com menos de 1 s, e um segundo alarme dentro de um episódio que já foi detectado.

Com isso:

| Métrica | Fórmula |
| --- | --- |
| Recall | R = acertos / episódios de 1 s ou mais |
| **Precisão por alarme** | P = acertos / (acertos + falsos alarmes) |
| **F1** | F1 = 2·P·R / (P + R) |
| **F2** | F2 = 5·P·R / (4·P + R) |

O F2 é o caso β = 2 da fórmula geral F_β = (1 + β²)·P·R / (β²·P + R) (van Rijsbergen, *Information Retrieval*, 1979). Quando não há acertos, P, F1 e F2 valem 0, como no `f1_evento` de hoje.

**Uma ressalva sobre o nome "precisão por alarme":** o numerador conta episódios detectados, e não alarmes certos. Os alarmes extras dentro de um mesmo episódio e os alarmes em episódios curtos ficam de fora. Isso segue a convenção do `f1_evento` que o projeto já usa, e a ressalva vai escrita no notebook junto da primeira tabela.

## Por que β = 2

- **Os dois erros têm custos diferentes.** Um microssono perdido pode virar acidente. Um alarme falso incomoda e não causa dano direto. Por isso o recall deve pesar mais.
- **O β não pode ser muito grande.** Alarmes falsos demais fazem o motorista ignorar ou desligar o sistema, e aí o recall alto não serve para nada. Com β muito grande, a métrica viraria só o recall, que já está nas tabelas.
- **β = 2 é o valor usual para "recall mais importante",** e foi o pedido da banca. Na definição de van Rijsbergen, β é quantas vezes o recall importa mais que a precisão.
- **O β = 2 é uma convenção, não uma conta de custo.** Não temos dados para estimar o custo real de cada erro. Por isso o F1 é reportado sempre ao lado do F2, e as colunas de recall e de falsos alarmes continuam nas tabelas.

O β fica fixo em 2. Não testamos outros valores de β para ver qual favorece este ou aquele sinal.

## O que **não** muda: a escolha do limiar continua pelo F1

Hoje, o limiar de olho de cada vídeo é o de maior F1 de evento nos outros 43 vídeos (`deixar_um_video_de_fora`), e o limiar do holdout é o de maior F1 nos 39 vídeos de calibração (`limiar_na_calibracao`). **Isso continua igual.** O F2 entra só como métrica reportada.

- **Motivo:** escolher o limiar pelo F2 mudaria os limiares e, com eles, os acertos e os falsos alarmes de todas as tabelas. Seria um sistema novo, e não uma métrica nova sobre o mesmo sistema.
- **Consequência:** o F2 reportado não é o maior F2 possível de cada sinal, porque o limiar foi escolhido pelo F1. Isso vale igual para todos os sinais, então a comparação entre eles continua justa.
- **Escolher o limiar pelo F2** fica fora deste protocolo. Se o grupo quiser testar, isso vira um teste novo, com protocolo próprio, e não pode usar o resultado daqui para decidir.

## Como agregar

- **Validação cruzada (44 vídeos):** as contagens são somadas em todos os vídeos, e P, R, F1 e F2 saem das somas (agregação "micro"). É o mesmo modo do recall das tabelas atuais.
- **Classificadores com 5 sementes:** as contagens por vídeo são a média das 5 sementes, como em `por_video` (seção 6.1) e `media_por_video` (seção 5), e as métricas saem dessas médias. Na tabela por semente da seção 5, cada semente ganha também o próprio F1 e F2, e o resumo mostra a média e o desvio entre sementes, como as outras colunas.
- **Holdout:** P, F1 e F2 saem das contagens do holdout de cada semente, e a tabela mostra a média das 5 sementes, como hoje.

## Em quais tabelas entram

Em todas, as colunas de hoje continuam. Entram três colunas novas: **precisão por alarme, F1 e F2**.

| Seção | Tabela | Sem filtro | Com filtro | Holdout |
| --- | --- | --- | --- | --- |
| 2.3 | Varredura de T com o EAR (calibração e teste) | Sim (só F2; o F1 já está) | — | Já está (a varredura do teste é o holdout) |
| 2.3 | EAR com T = 1 s, holdout | Sim | — | Sim |
| 5 | Tabela por semente e resumo (média ± desvio) | Sim, na validação cruzada e no holdout | — | Sim |
| 5 | Diferenças pareadas entre sinais | Sim (F1 e F2 com IC) | — | Não |
| 6.1 | Validação cruzada, EAR, MobileNet e YOLO | Sim | Sim | — |
| 6.1 | Holdout, EAR, MobileNet e YOLO | Sim | Sim | Sim |
| 6.1 | Efeito do filtro e diferenças entre sinais | Sim (F1 e F2 com IC) | Sim (F1 e F2 com IC) | Não |
| 6.3 | Validação cruzada, EAR, YOLO e as duas fusões | — | Sim | — |
| 6.3 | Holdout com o limiar da calibração | — | Sim | Sim |
| 6.3 | Diferenças pareadas | — | Sim (F1 e F2 com IC) | Não |

**A varredura de T da seção 2.3 é uma exceção:** ela usa todos os episódios, inclusive os de menos de 1 s, porque mostra a troca entre T curto e T longo. O F2 ali segue a mesma definição do F1 que já está lá, e a tabela continua sendo só ilustração, porque o T é fixo em 1 s.

**Ficam de fora:**
- **Seção 4.2:** o F1 já é o critério de escolha dos ajustes ali, e mexer na tabela não acrescenta nada à pergunta da banca.
- **Seção 6.2 (piscadas):** os frames recolocados do NITYMED não têm rótulo, então não dá para calcular a precisão.
- **Seção 7 (agente de RL):** o agente é um experimento fora do pipeline, e a recompensa dele já tem o próprio peso entre acerto e alarme (λ).

**Holdout:** entra, mas só como descrição. São 14 episódios de 1 s ou mais em 2 vídeos, e de 0,6 a 7 falsos alarmes por sinal, então um único alarme muda a precisão em vários pontos. O holdout não tem intervalo nem comparação, como hoje.

## Incerteza e comparações

- **Intervalo:** bootstrap por vídeo, pareado, com 5.000 sorteios, semente `SEMENTE` e IC95% pelos percentis 2,5 e 97,5. É o mesmo método das funções `diferenca` (seção 5) e `diferenca_pareada` (seções 6.1 e 6.3).
- **Mesmos sorteios:** em cada sorteio, os mesmos vídeos entram nos dois sinais, e o F1 e o F2 de cada sinal são calculados das contagens somadas desse sorteio. Os sorteios são exatamente os mesmos que já dão os intervalos de recall e de falsos alarmes, então esses intervalos não mudam.
- **Comparações reportadas:** só as que o notebook já reporta, agora com a diferença de F1 e de F2 e o intervalo de cada uma:

| Seção | Comparações (a − b) |
| --- | --- |
| 5, sem filtro | YOLO − MobileNet; YOLO − EAR; MobileNet − EAR |
| 6.1 | Com filtro − sem filtro, em cada um dos 3 sinais; com filtro: YOLO − EAR, YOLO − MobileNet, MobileNet − EAR |
| 6.3, com filtro | Fusão média − EAR; Fusão média − YOLO; Fusão mínimo − EAR; Fusão mínimo − YOLO; Fusão média − Fusão mínimo |

- **Leitura:** uma diferença só conta como conclusiva se o IC95% não incluir zero, como em todo o notebook. Não acrescentamos comparações novas depois de ver as diferenças.
- **Intervalo de cada sinal sozinho:** não entra. As perguntas do notebook são comparações, e o intervalo da diferença pareada é o que responde a elas.

## Conferência da implementação

A implementação só acrescenta colunas. Ela não muda `avaliar_eventos`, `contagens`, `deixar_um_video_de_fora`, `limiar_na_calibracao`, o filtro nem as sementes. Antes de mexer em qualquer texto, conferimos:

1. **Acertos, episódios e falsos alarmes iguais aos de hoje** em todas as tabelas acima. Por exemplo, na validação cruzada com filtro: EAR 141 de 165 com 16 falsos, MobileNet 125,4 com 17,8, YOLO 143,2 com 10,2 e Fusão média 149,6 com 6,0. Os intervalos de recall e de falsos alarmes também têm de ser iguais aos de hoje.
2. **A fórmula nova reproduz o F1 antigo:** com β = 1, a função nova dá o mesmo valor que `f1_evento` e que a coluna "F1 evento" da varredura de T.
3. **A tabela nova é mostrada ao Rafael antes** de qualquer mudança no texto das observações, no resumo (seção 9), no `README.md` e no `CLAUDE.md`.

Se a execução for numa GPU diferente da RTX 3050 do Rafael, os números do YOLO podem mudar um pouco (seção 7 e `CLAUDE.md`). Nesse caso, a conferência 1 vale para o EAR, e as diferenças do YOLO são registradas, e não corrigidas.

## Riscos conhecidos

- **A precisão depende de quantos microssonos há.** No FL3D, há 165 episódios de 1 s ou mais em cerca de 46 minutos de vídeo, porque os vídeos parecem seguir um roteiro. Numa viagem real, os microssonos são raros, então os mesmos alarmes falsos por hora dariam uma precisão muito menor. **A precisão, o F1 e o F2 do FL3D servem para comparar sinais na mesma base, e não descrevem o sistema numa viagem.** Isso vai escrito no notebook e no paper. A taxa de alarmes por hora em pessoas acordadas (seção 8.2) continua sendo a medida para isso.
- **O FL3D não tem piscadas,** então a precisão do FL3D sai otimista (seção 6.2).
- **Poucos falsos alarmes com filtro** (de 6 a 18 na validação cruzada): pequenas mudanças viram vários pontos de precisão.
- **A separação é por vídeo, e não por motorista,** como em toda a avaliação no FL3D.
- **A fusão da seção 6.3 nasceu de olhar as seções 5 e 6,** nos mesmos 44 vídeos. O F2 dela herda esse otimismo.

## Relação com o critério do modelo final (seção 10.4)

A seção 10.4 propõe escolher o sistema de microssono pelo maior F2 na validação cruzada do FL3D. Este protocolo só calcula o F2 e os intervalos. Ele não decide o modelo final. O critério da 10.4 ainda precisa ser aprovado pelo grupo, e a forma de ler o F2 ali (só o valor pontual ou o intervalo da diferença) é decidida nesse critério, antes de ver as diferenças de F2 calculadas aqui.

## O que fica fora

- Mudar β, a tolerância de 0,5 s, a duração mínima de 1 s, o T, o filtro ou os limiares depois de ver o F2.
- Escolher o limiar pelo F2 (só com protocolo novo).
- Acrescentar comparações, sinais ou bases além das listadas.
- Mudar `avaliar_eventos` para contar a precisão alarme por alarme. Isso mudaria a definição usada desde a seção 2, e fica como possível melhoria para depois.
