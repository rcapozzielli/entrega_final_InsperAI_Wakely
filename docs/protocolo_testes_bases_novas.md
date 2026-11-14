# Protocolo: alarmes de microssono nas bases novas (condição 2 da seção 10.4)

Escrito em 13/11/2026 pelo Antônio, **antes de rodar qualquer sistema nas bases novas** (os sinais estavam sendo extraídos, nenhum alarme tinha sido calculado). Complementa o critério aprovado na seção 10.4 e as definições de `docs/protocolo_metricas_f.md`, sem mudar nenhum dos dois.

## O que se mede

A seção 10.4 diz que um candidato só substitui o sistema atual (YOLO com filtro) se, além de ganhar em F2 no FL3D, **não der mais alarmes falsos por hora** somando as bases de teste. A frente B já mostrou a condição 1 para a fusão pela média (+0,037 de F2, de +0,010 a +0,071). Aqui se mede a condição 2, e também o microssono na BINUS.

## Sistemas (nada é escolhido aqui)

| Sistema | Sinal | Limiar | Resto |
|---|---|---|---|
| Atual | P(fechado) do YOLO (semente 42), média dos dois olhos | 0,4 (seção 7) | Filtro de bocejo, T = 1 s, um alarme por trecho |
| Fusão pela média | (fechamento pelo EAR + P(fechado)) / 2, com o fechamento = 1 − EAR ÷ mediana do EAR nos primeiros 30 s com rosto, cortado em [0, 1] | 0,35 (escolhido na calibração do FL3D, seção 6.3) | Igual |

A regra é a da demo (`demo/alerta.py`), que repete a do notebook. Os sinais vêm do mesmo `ExtratorRosto` da demo, um quadro por vez, na taxa de quadros de cada base (`experimentos/extrair_sinais.py`).

## Bases e como cada uma conta

| Base | O que conta | Duração |
|---|---|---|
| **Eyeblink8** (8 vídeos, 4 pessoas, 640×480, 30 fps) | Ninguém dorme: **todo alarme de microssono é falso**. Reportado também quantos caem perto de uma piscada anotada | ~40 min |
| **Drive&Act**, câmera da coluna A do motorista (30 vídeos, 15 pessoas, infravermelho próximo, 30 fps) | Simulador, motoristas acordados: **todo alarme é falso**. Reportado também por atividade anotada | ~11,4 h |
| **UTA-RLDD, classe alerta** | Todo alarme é falso, como na seção 8.2, com os sinais em cache da seção 8.5 (10 fps) | ~9,5 h |
| **BINUS**, 47 vídeos de teste (um quadro a cada 5, ou 6 por segundo) | **Microssono:** recall nos fechamentos de 1 s ou mais, precisão por alarme, F1 e F2, com as definições da frente B. **Falso alarme:** alarme fora de qualquer fechamento anotado, com tolerância de 0,5 s | ~47 min |

**Olho fechado na BINUS (definido antes de olhar):** o quadro conta como fechado quando todas as caixas de olho do quadro são `mata_tertutup` (olho fechado) e há pelo menos uma. Os trechos fechados separados por até 0,5 s viram um só episódio, como no FL3D. A duração é (último quadro − primeiro) ÷ 30 + 1/6 s. Conferência: o docs/bases_candidatas.md fala em 93 fechamentos de 1 s ou mais; se a contagem daqui sair diferente, a diferença é registrada, e a definição não muda.

**Taxa de alarmes falsos:** total de alarmes falsos ÷ total de horas de vídeo, somando Eyeblink8, Drive&Act e UTA alerta (pesando cada base pelo tempo), como manda a 10.4. Cada base também é reportada separada. A BINUS não entra nessa soma, porque tem microssono encenado.

**Incerteza:** bootstrap pareado por vídeo (por pessoa no UTA), 5.000 sorteios, IC95% pelos percentis 2,5 e 97,5, para a diferença fusão − atual nos alarmes por hora e no F2 da BINUS.

## Leitura

- A fusão **passa na condição 2** se a taxa somada não for maior que a do sistema atual (o critério da 10.4 compara os valores, sem exigir intervalo).
- O intervalo é reportado para mostrar o quanto a diferença é incerta.
- Nada é ajustado depois: nem limiar, nem filtro, nem a definição de olho fechado da BINUS.

## Mudança em 13/11, antes de contar qualquer alarme: Drive&Act fora

Na extração dos sinais, o MediaPipe achou o rosto em só **1% a 28% dos quadros** dos 9 primeiros vídeos do Drive&Act (câmera `a_column_driver`, que filma o motorista de lado, em infravermelho). Sem rosto não há alarme, então as 11,4 h da base diluiriam a taxa de alarmes falsos dos dois sistemas e não testariam nada. **O grupo decidiu (Antônio e Rafael, 13/11) tirar o Drive&Act da condição 2** e ficar com o **Eyeblink8 e a classe alerta do UTA-RLDD**. A extração foi interrompida, e nenhum alarme do Drive&Act foi calculado. Outra câmera do Drive&Act mais de frente (espelho interno ou Kinect) fica como trabalho futuro.

## Correção de um erro de nome na BINUS (13/11)

O protocolo dizia que "olho fechado" na BINUS é `mata_tertutup`. Na base, o rótulo é `mata_terpejam` (os rótulos são `mata_terbuka` aberto, `mata_terpejam` fechado, `menguap` bocejo e `tidak_menguap` sem bocejo). A primeira execução achou 0 episódios por causa desse nome errado. O nome foi corrigido; a definição (todas as caixas de olho do quadro fechadas, pelo menos uma caixa) não mudou. Os alarmes da primeira execução não entram em nenhuma conclusão.

## Riscos

- **Drive&Act é infravermelho próximo**, como o treino do YOLO (MRL), mas com outra câmera e outro ângulo. O MediaPipe pode achar menos rostos; a fração com rosto é reportada.
- **A BINUS tem 6 quadros por segundo,** e não 25 ou 30. A regra de tempo funciona em segundos, mas o filtro de bocejo e a junção de buracos foram pensados em 25 fps.
- **Microssonos encenados** na BINUS.

## Correção em 14/11, depois de rodar: referência do EAR

A tabela de sistemas acima diz "mediana do EAR nos primeiros 30 s com rosto". Isso estava errado: a fusão que passou na condição 1 (seção 6.3) usa o **percentil 75** do EAR nos primeiros 30 s (`referencia`, seção 2.1), e o objetivo deste protocolo era medir **esse** sistema. A correção não escolhe nada olhando o resultado: ela só faz o código seguir a definição do notebook. As duas versões estão no registro (`docs/registro_antonio_13-11.md`, seção 3), e a fusão passa na condição 2 com as duas (5,5 e 5,7 por hora, contra 6,6 do YOLO).
