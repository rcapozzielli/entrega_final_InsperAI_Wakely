# Registro de trabalho do Antônio (13/11/2026), branch `feat/laya-e-testes`

Feito com o Claude Code, a partir da branch `feat/pos-intermediaria` do Rafael (commit 3390279). Nada aqui mexe no `wakely.ipynb`. Os scripts estão em `experimentos/`, e os dados e caches em `data/` (fora do Git).

## 1. Sinais extraídos

`experimentos/extrair_sinais.py` passa cada vídeo pelo mesmo `ExtratorRosto` da demo (`demo/sonolencia.py`) e guarda os 61 sinais por quadro (P(fechado) do YOLO semente 42, EAR, boca, rosto, pose da cabeça e blendshapes) em `data/cache/sinais/<vídeo>.npz`.

| Vídeo | Quadros | fps | Rosto achado |
|---|---|---|---|
| silencioso, de óculos | 24.908 | 30 | 88,6% |
| v1, alerta, de óculos (sem planilha de rótulos) | 1.969 | 30 | 97,3% |
| v2, celular, sem óculos | 4.114 | 30 | 100% |
| v3, microssono encenado, de óculos | 5.277 | 30 | 100% |

`experimentos/extrair_fl3d.py` faz o mesmo nos 53.329 quadros do FL3D, na ordem da tabela `fl3d` da seção 1, porque o cache do FL3D não tinha a pose da cabeça.

## 2. Gravações do Antônio: onde o sistema erra (EXPLORATÓRIO)

Pela seção 10.3, as gravações só servem para achar falhas e propor filtros. **Nenhum número desta seção é resultado do sistema.** Script: `experimentos/explorar_gravacoes.py`. Sistemas exatamente como no notebook e na demo: YOLO com filtro (limiar 0,4) e fusão pela média (limiar 0,35), os dois com T = 1 s e o mesmo filtro de bocejo.

| Gravação | Sistema | Microssonos de 1 s ou mais achados | Alarmes em trechos de celular | Alarmes fora de trechos rotulados |
|---|---|---|---|---|
| silencioso (óculos) | YOLO | 2 de 2 | 2 | 15 |
| silencioso (óculos) | Fusão | 2 de 2 | 4 | 20 |
| v2, celular (sem óculos) | YOLO | — | 4 | 0 |
| v2, celular (sem óculos) | Fusão | — | 3 | 0 |
| v3, microssono (óculos) | YOLO | 6 de 6 | — | 3 |
| v3, microssono (óculos) | Fusão | 6 de 6 | — | 3 |

Os "fora de trechos rotulados" do vídeo silencioso caem nos 11 minutos sem rótulo, em que o Antônio estava na aula fazendo outras coisas; não dá para dizer se são falsos alarmes.

**O que a exploração mostra:**
- **Olhar o celular no colo dispara microssono** nos dois sistemas. O P(fechado) mediano nesses trechos fica entre 0,18 e 0,46, perto do limiar, porque as pálpebras descem quando a pessoa olha para baixo.
- **A pose da cabeça sozinha não separa celular de microssono.** O pitch (graus em relação aos primeiros 30 s) foi de +13 a +20 no celular, mas de +10 a +17 nos microssonos encenados com a cabeça caindo. Um filtro do tipo "cabeça baixa → ignorar o olho fechado" apagaria justamente os microssonos com a cabeça caindo, o caso mais perigoso.
- **O que mais separou foi o próprio P(fechado):** de 0,18 a 0,46 no celular contra 0,61 a 0,99 nos microssonos (exceto o mais curto, 0,51). Isso sugere que um filtro de distração precisa combinar a pose com a intensidade do fechamento.
- **Isso é uma hipótese, não um resultado:**  (continua abaixo)

## 3. Microssono nas bases novas: YOLO com filtro × fusão pela média (protocolo `docs/protocolo_testes_bases_novas.md`)

Script: `experimentos/testes_bases_novas.py`. Sistemas idênticos aos do notebook (0,4 e 0,35, filtro de bocejo, T = 1 s), sinais do `ExtratorRosto` da demo, regra quadro a quadro. O Drive&Act saiu antes de contar alarmes (rosto achado em 1% a 28% dos quadros).

**Correção em 14/11 (referência do EAR na fusão):** a primeira execução usou, por engano, a **mediana** do EAR nos primeiros 30 s como referência da fusão, como estava escrito no protocolo. A fusão aprovada na condição 1 (seção 6.3) usa o **percentil 75** (`referencia`, seção 2.1). O código foi corrigido para o percentil 75 e tudo foi rodado de novo; as tabelas abaixo já são as corrigidas. A conclusão não muda. Valores da primeira execução, com a mediana: UTA 4,6/h, total 5,5/h (−1,1, de −5,2 a +1,3), BINUS 44 achados e F2 0,337. O Eyeblink8 e o holdout do FL3D deram iguais. A demo do PR da fusão foi corrigida do mesmo jeito.

### Condição 2 da seção 10.4: alarmes de microssono por hora em pessoas acordadas

| Base | Vídeos | Horas | Rosto achado | YOLO com filtro | Fusão pela média | Fusão − YOLO (IC95%) |
|---|---|---|---|---|---|---|
| Eyeblink8 | 8 | 0,66 | 99,7% | 10,6 /h | 18,2 /h | +7,6 /h (+2,4 a +15,0) |
| UTA-RLDD, classe alerta | 60 | 9,53 | 100% | 6,3 /h | 4,8 /h | −1,5 /h (−5,6 a +0,8) |
| **Total, pesado pelo tempo** | 68 | 10,19 | 99,9% | **6,6 /h** | **5,7 /h** | −0,9 /h (−4,8 a +1,5) |

- **Pelo critério da 10.4, a fusão passa na condição 2:** a taxa somada (5,7 por hora) não é maior que a do YOLO (6,6 por hora). Junto com a condição 1, já medida pelo Rafael, a fusão vira o sistema de microssono.
- **A diferença no total não é conclusiva:** o intervalo vai de −4,8 a +1,5 por hora.
- **No Eyeblink8 a fusão é pior, de forma conclusiva** (+7,6 por hora, intervalo sem zero). O Eyeblink8 é uma webcam comum em ambiente interno, com piscadas rápidas, que é o caso mais parecido com a demo. Pela 10.4, essa piora numa base isolada entra como limitação no paper.
- O UTA pesa 94% das horas, então o total segue o UTA.

### BINUS: microssono fora do FL3D (47 vídeos, 46,8 min, 6 quadros por segundo)

| Sistema | Episódios de 1 s ou mais | Achados | Recall | Falsos alarmes | Precisão por alarme | F1 | F2 |
|---|---|---|---|---|---|---|---|
| YOLO com filtro | 152 | 48 | 0,316 | 4 (5,1/h) | 0,923 | 0,471 | 0,364 |
| Fusão pela média | 152 | 46 | 0,303 | 0 (0,0/h) | 1,000 | 0,465 | 0,352 |

- **Fusão − YOLO, F2:** −0,012 (IC95% de −0,052 a +0,025), sem diferença conclusiva. Recall: de −0,051 a +0,022. Falsos alarmes: de −10 a 0.
- **Os dois sistemas acham só cerca de 30% dos fechamentos de 1 s ou mais na BINUS,** contra cerca de 90% no FL3D. O motivo ainda não foi investigado. Hipóteses a conferir: a BINUS tem 6 quadros por segundo (a regra foi pensada para 25), o rótulo é por caixa desenhada à mão a cada 5 quadros, e as pessoas, câmeras e acessórios (óculos, boné, hijab) são diferentes. Essa queda é o resultado mais importante desta etapa, porque mostra o quanto o FL3D é otimista.
- **Contagem de episódios diferente da do Rafael:** aqui deram 152 fechamentos de 1 s ou mais; o `docs/bases_candidatas.md` fala em 93. A definição deste protocolo (todas as caixas de olho fechadas, buracos de até 0,5 s juntados) foi mantida. A diferença precisa ser conferida com o Rafael antes do paper.
- Primeira execução com o nome do rótulo errado (`mata_tertutup` em vez de `mata_terpejam`): achou 0 episódios e foi descartada; ver o protocolo.

## 3b. Laya como camada de decisão do microssono (protocolo `docs/protocolo_laya.md`)

Script: `experimentos/laya_cerebro.py` (etapas `logistica`, `finetune`, `prever_laya`, `avaliar`). Janelas de 2 s a cada 0,5 s, com os 12 campos fixados no protocolo, montadas por `experimentos/construir_janelas.py`.

**O que rodou:**
- Treino nas 4.778 janelas dos 39 vídeos de calibração do FL3D (4.215 `normal`, 563 `microssono`).
- Laya com fine-tuning, 4 épocas, micro-lote 1, acumulação de 32, **só a semente 0** (141 min na RTX 4060). As sementes 1 e 2 foram canceladas por tempo, antes de qualquer previsão (registrado no protocolo). Um primeiro treino da semente 0, interrompido em 13/11, foi descartado; o novo deu o mesmo loss por época (1,47, 1,27, ...), o que mostra que a semente reproduz o treino.
- Regressão logística nos mesmos campos, como linha de base.
- A regra atual (YOLO com filtro) e a fusão foram medidas quadro a quadro, como sempre, e deram os mesmos números da seção 3.

### Resultados nas bases de teste

| Base | Sistema | Achados (de 1 s ou mais) | Falsos | Falsos por hora | Recall | Precisão | F2 |
|---|---|---|---|---|---|---|---|
| BINUS (47 vídeos, 152 episódios) | YOLO com filtro | 48 | 4 | 5,1 | 0,316 | 0,923 | 0,364 |
| | Fusão | 46 | 0 | 0,0 | 0,303 | 1,000 | 0,352 |
| | Logística | 58 | 9 | 11,5 | 0,382 | 0,866 | 0,430 |
| | **Laya (semente 0)** | **83** | 6 | 7,7 | **0,546** | 0,933 | **0,595** |
| FL3D holdout (5 vídeos, 14 episódios) | YOLO com filtro | 13 | 2 | 21,9 | 0,929 | 0,867 | 0,915 |
| | Fusão | 12 | 1 | 10,9 | 0,857 | 0,923 | 0,870 |
| | Logística | 1 | 0 | 0,0 | 0,071 | 1,000 | 0,088 |
| | Laya (semente 0) | 13 | 6 | 65,7 | 0,929 | 0,684 | 0,867 |
| Eyeblink8 (8 vídeos, ninguém dorme) | YOLO com filtro | — | 7 | **10,6** | — | — | — |
| | Fusão | — | 12 | 18,2 | — | — | — |
| | Logística | — | 98 | 148,3 | — | — | — |
| | Laya (semente 0) | — | 23 | **34,8** | — | — | — |

Diferenças (bootstrap pareado por vídeo, 5.000 sorteios, IC95%):
- **BINUS, F2:** Laya − YOLO **+0,232 (+0,118 a +0,352)**; Laya − logística **+0,166 (+0,086 a +0,249)**; Laya − fusão +0,244 (+0,140 a +0,355).
- **Eyeblink8, falsos por hora:** Laya − YOLO **+24,2 (+4,8 a +55,6)**; Laya − fusão +16,7 (−1,1 a +46,7); Laya − logística −113,5 (−176,5 a −62,2).
- **FL3D holdout, F2:** Laya − YOLO −0,049 (−0,082 a 0,000). Só 5 vídeos e 14 episódios: confirmação fraca, como dizia o protocolo.

### Leitura pelo critério do protocolo

| Condição | Resultado |
|---|---|
| 1. F2 maior que a regra atual, IC sem zero | **Passa** na BINUS (+0,23) |
| 2. Alarmes falsos por hora não maiores que a regra atual | **Falha**: 34,8 por hora contra 10,6 no Eyeblink8, de forma conclusiva |
| 3. Melhor que a logística com os mesmos campos, IC sem zero | **Passa** (+0,17 de F2 na BINUS) |

**Conclusão: pelo critério fixado antes, o Laya não substitui a regra atual,** porque dispara mais que o triplo de alarmes falsos em pessoas acordadas. Mas há dois achados que valem para o paper:
- **Na BINUS, o Laya achou 83 dos 152 microssonos, contra 48 da regra,** sem perder precisão (0,93). É a primeira coisa testada que melhora a queda de recall da BINUS (seção 3). Como ele ganha da logística com os mesmos campos, o ganho não vem só dos campos do JSON.
- **O custo são os alarmes em piscadas rápidas** (Eyeblink8) e no FL3D holdout (6 falsos contra 2). Uma hipótese, não testada: a decisão por janela dispara com uma janela só, sem a espera de T = 1 s da regra.

**Limitações:**
- Uma semente só, então não se sabe a variação entre treinos.
- Microssonos encenados na BINUS.
- A condição 2 ficou só com o Eyeblink8 (0,66 h), porque o UTA não fazia parte deste protocolo.
- O protocolo não previa juntar o Laya com o tempo mínimo da regra (por exemplo, exigir duas janelas seguidas). Isso é **trabalho futuro**, e teria que ser fixado e testado em outra base para não escolher olhando a BINUS e o Eyeblink8.

### Segunda tentativa: Laya com espera de 1 s (2 janelas seguidas)

Protocolo escrito antes de rodar (fim de `docs/protocolo_laya.md`); script `experimentos/laya_espera.py`. O mesmo modelo da semente 0, sem treinar de novo; o alarme só dispara com 2 janelas `microssono` seguidas. Nenhum outro valor foi testado.

**Confirmatório, UTA-RLDD classe alerta** (60 pessoas, 9,53 h, 68.355 janelas, base que nenhum modelo de janela viu; todo alarme é falso):

| Sistema | Alarmes falsos por hora |
|---|---|
| YOLO com filtro (regra atual) | **6,3** |
| Fusão | **4,8** |
| Laya, 1 janela | 43,8 |
| **Laya, 2 janelas** | **21,6** |
| Logística, 1 janela | 141,8 |
| Logística, 2 janelas | 121,2 |

- Laya com espera − regra atual: **+15,3 por hora (IC95% +6,4 a +27,3)**. **Falha na condição 2**, de forma conclusiva.
- Laya com espera − fusão: +16,8 (+6,7 a +29,8). Laya com espera − logística com espera: −99,5 (−139,7 a −64,5).

**Exploratório (bases já vistas):** a espera cortou os alarmes falsos no Eyeblink8 (34,8 → 19,7 por hora, ainda acima dos 10,6 da regra), mas **levou junto o ganho na BINUS:** 56 de 152 achados (F2 0,419) contra 83 (0,595) sem espera e 48 (0,364) da regra. No holdout do FL3D, caiu para 5 de 14.

**Conclusão das duas tentativas:**
- O Laya, decidindo sobre os mesmos sinais do Wakely, **não substitui a regra de tempo**.
- O ganho de recall na BINUS vinha de disparar cedo, com uma janela só. Ao exigir o mesmo 1 s da regra, ele quase desaparece, e os alarmes falsos em pessoas acordadas continuam de 3 a 4 vezes os da regra.
- **O Laya sempre ganhou da logística com os mesmos campos,** o que mostra que ele aprende alguma coisa dos números, mas não o bastante para o uso.
- Fica no paper como **experimento negativo, documentado**. A decisão do Wakely continua sendo a regra, com a fusão.

## 4. Gravações: continuação

- **Isso é uma hipótese, não um resultado:** vem de uma pessoa, com microssonos encenados. Ela precisa ser confirmada em pessoas que não participaram da ideia, como manda a 10.3 (Drive&Act).
