# Protocolo do modelo final de sonolência: teste externo na SUST-DDD

Escrito em 13/11/2026, **antes de extrair os sinais da SUST-DDD e antes de calcular o PERCLOS adaptativo e o PERCLOS combinado com a MIL em qualquer base**. Aprovado pelo Rafael em 13/11/2026, antes da extração. O protocolo não muda depois disso. Qualquer conta fora dele entra no notebook marcada como exploratória.

## Por que este protocolo

O paper precisa dizer qual é o modelo final de sonolência, a que vem antes do microssono. A seção 10.4 propunha este critério: **uma rede só vira o modelo final se superar o PERCLOS absoluto com intervalo de confiança acima de zero numa base que não foi usada para escolhê-la, sem perder no UTA nem no DROZY. Se nenhuma passar, o modelo final de sonolência é o PERCLOS absoluto.**

**Mudança de critério em 13/11/2026, decidida pelo Rafael antes de extrair a SUST, mas depois de ver o UTA e o DROZY.** O critério da 10.4 mistura duas perguntas:

1. qual modelo usar no sistema final;
2. se podemos afirmar que ele supera o PERCLOS.

Com uma base nova pequena (34 sequências de 15 motoristas), exigir IC acima de zero só nela pode descartar um modelo que não é pior, só porque a base é pequena. Por isso o critério passa a ter dois níveis: **a escolha pela média das bases** e **a afirmação de superioridade só com IC acima de zero na SUST** (ver "Regra de decisão").

A mudança foi feita conhecendo o UTA e o DROZY, então ela favorece quem já ia bem nessas duas bases. Isso é registrado na seção 10.4 e no paper, e o grupo é avisado.

A base nova é a **SUST-DDD**: 19 motoristas em direção real (20 grupos depois do agrupamento à mão de 13/11), gravando com o próprio celular, com clipes de 10 s rotulados por observadores como sonolento ou não. É a única base com vídeo do rosto que ainda não usamos. O WACHsens não tem vídeo do rosto e não entra aqui.

## O que já se sabe antes deste protocolo

**Seção 8.7 (AUC por vídeo, sem o minuto de calibração, redes com a média de 5 sementes):**

| Modelo | UTA (118 vídeos) | DROZY (36 vídeos) |
|---|---|---|
| PERCLOS absoluto | 0,814 | 0,619 |
| MIL-GRU-4 híbrida | 0,742 | 0,708 |
| MIL-Transformer-14 híbrido | 0,875 | 0,743 |

- **MIL-GRU-4 menos PERCLOS absoluto:** −0,071 no UTA (de −0,144 a −0,004) e +0,089 no DROZY (de −0,159 a +0,293).
- **A diferença MIL-Transformer menos PERCLOS absoluto** nunca foi calculada em nenhuma das duas bases.
- **Ainda não foram calculados em nenhuma base:** o PERCLOS adaptativo e o PERCLOS combinado com a MIL. Nenhum sinal da SUST foi extraído.

**Checagem de viabilidade da SUST, feita antes de escrever (13/11), sem usar rótulo nem calcular resultado:**
- 12 clipes de 6 motoristas, 30 quadros cada, todos em 720×1280;
- o rosto foi achado nos 360 quadros, com olho de 22 a 58 px de largura e cerca de 20 ms por quadro.

**Contagem das sequências remontadas, também só com a estrutura da base:**
- sequências de 2 min ou mais: 34 (14 sonolentas e 20 não sonolentas), de 15 motoristas;
- 7 motoristas têm as duas classes;
- os minutos avaliados por sequência vão de 1 a 9, com mediana de 2.

## Candidatos

| Candidato | Entrada | Papel |
|---|---|---|
| **PERCLOS absoluto** | Média do PERCLOS dos minutos avaliados (fração dos quadros com rosto em que P(fechado) ≥ 0,5) | Referência. Também concorre na escolha pela média |
| **MIL-Transformer-14 híbrido** | O da seção 8.7, treinado no UTA inteiro | Desafiante |
| **PERCLOS combinado com a MIL** | Média de dois sinais padronizados: o PERCLOS absoluto e o logit da P(sonolento) da MIL-GRU-4 | Desafiante |
| **PERCLOS adaptativo** | PERCLOS com o limiar relativo ao olho aberto da própria pessoa | Desafiante |
| **MIL-GRU-4 híbrida** | A da demo (`data/modelos/mil_gru4_uta.pt`) | **Só descrição.** Pela trava deste protocolo, ela já perde no UTA (IC de −0,144 a −0,004, todo abaixo de zero), então não pode virar o modelo final. Ela é reportada porque está na demo e entra no candidato combinado |

### Definições dos candidatos novos, fixadas agora

**PERCLOS combinado com a MIL.** Ataca o custo da normalização: o PERCLOS absoluto guarda o nível de olho fechado, que a MIL apaga ao subtrair o 1º minuto, e a MIL guarda a mudança ao longo do vídeo.

- **Sinais:** o PERCLOS absoluto por vídeo e o logit da P(sonolento) da MIL-GRU-4 (média das 5 sementes).
- **Padronização:** cada um é padronizado com a média e o desvio dos 118 vídeos do UTA, sem usar rótulo.
- **Nota final:** a média dos dois sinais padronizados. Não há nada treinado além disso.
- **Por que a GRU-4, e não o Transformer:** ela é a rede principal da 8.7 e a que está na demo. Escolher o Transformer seria escolher depois de ver o resultado.
- **No UTA,** a P da MIL é a previsão fora da dobra da seção 8.7.

**PERCLOS adaptativo.** É a mesma linha de base do rascunho do microssono (`docs/protocolo_limiar_adaptativo.md`), para que o sistema use uma adaptação só.

- **Linha de base:** b = percentil 25 do P(fechado) nos primeiros 30 s do minuto de calibração, só nos quadros com rosto.
- **Olho fechado:** um quadro conta como fechado quando (P − b) / (1 − b) ≥ 0,5, ou seja, P ≥ b + 0,5·(1 − b).
- **PERCLOS:** a fração dos quadros com rosto que contam como fechados, na média dos minutos avaliados.
- **Calibração recusada:** se a janela tiver menos de 5 s com rosto, ou se b > 0,5, a sequência usa b = 0, que é o PERCLOS absoluto. O número de calibrações recusadas é reportado em cada base.
- **Diferença para o ΔPERCLOS da 8.7:** o ΔPERCLOS subtrai o PERCLOS inteiro do 1º minuto e apaga o sono de quem já começa sonolento. O adaptativo só desconta o P(fechado) do olho aberto, e a frequência de fechamentos continua no sinal.

O P(fechado) é sempre a média dos dois olhos, como nos atributos da seção 8.2.

## Regra de decisão

A regra tem dois níveis, e os dois são reportados.

### Nível 1: escolha do modelo final (o que vai na demo e no paper)

Fica o candidato com a **maior AUC média nas 3 bases** (UTA, DROZY e SUST). A trava vem antes da média e exclui qualquer candidato que perca de forma conclusiva em alguma base.

- **Candidatos:** o PERCLOS absoluto, o MIL-Transformer-14, o PERCLOS combinado e o PERCLOS adaptativo.
- **Média:** cada base pesa igual, e a média é simples: (AUC no UTA + AUC no DROZY + AUC na SUST) / 3. As redes entram com a média das 5 sementes em cada base.
- **Trava:** um desafiante só pode ser escolhido se, em nenhuma das 3 bases, o IC95% da diferença contra o PERCLOS absoluto ficar todo abaixo de zero. "Perder" é o IC todo abaixo de zero, a regra de conclusividade do notebook inteiro (decisão do Rafael em 13/11). A MIL-GRU-4 já não passa nessa trava.
- **Empate exato na média:** fica o PERCLOS absoluto, que é o mais simples.
- **Se a SUST não passar na checagem de qualidade,** a média usa só o UTA e o DROZY, e isso é registrado.

**O que já se sabe sobre o nível 1:** no UTA e no DROZY, o MIL-Transformer está +0,061 e +0,124 acima do PERCLOS absoluto. Para o PERCLOS absoluto ganhar dele na média, o Transformer teria de perder por mais de 0,185 de AUC na SUST. Por isso, o nível 1 tende a escolher o Transformer, a menos que um dos candidatos novos (combinado ou adaptativo), ainda não calculados, vá melhor. Essa conta é registrada agora, antes de rodar a SUST.

### Nível 2: afirmação de superioridade

Para afirmar no paper que o modelo escolhido **"supera o PERCLOS absoluto"**, a diferença de AUC na **SUST** precisa ter **IC95% acima de zero**. A SUST é a única base que não participou de nenhuma escolha.

| Resultado | Como escrever no paper |
|---|---|
| Escolhido = PERCLOS absoluto | "O modelo final de sonolência é o PERCLOS absoluto. Nenhum modelo o superou na média das bases." |
| Escolhido ≠ PERCLOS, com IC acima de zero na SUST | "O modelo X supera o PERCLOS absoluto, com confirmação numa base externa em direção real." |
| Escolhido ≠ PERCLOS, sem IC acima de zero na SUST | "O modelo X foi escolhido pela média das bases, mas a vantagem sobre o PERCLOS não foi confirmada na base nova." |

### Incerteza da média

A diferença de AUC média (candidato − PERCLOS absoluto) ganha um IC95% por bootstrap estratificado. Em cada sorteio, as pessoas ou motoristas são sorteados dentro de cada base, e a média das 3 diferenças sai desse sorteio (2.000 sorteios). O IC é só informativo: o nível 1 decide pelo valor pontual, e o nível 2, pelo IC da SUST.

### Riscos de múltiplos testes

São 3 desafiantes. Escolher o maior de vários valores pontuais favorece quem teve sorte, e isso entra como limitação. Não acrescentamos candidatos depois de ver os números.

## A SUST-DDD

**Unidade:** a sequência remontada (`data/cache/sust/sequencias.csv`), que é uma série de clipes contínuos da mesma classe. O motorista vem de `data/cache/sust/motoristas.csv` (20 grupos, agrupados à mão em 13/11, sem usar nenhum resultado).

**Minutos:** a cada 6 clipes contínuos de 10 s, um minuto de 600 quadros a 10 fps. Os clipes que sobram no fim da sequência ficam de fora, como os clipes curtos do UTA. O 1º minuto é o de calibração e sai da avaliação, como na 8.7.

**Sequências usadas no critério:** só as de **2 min ou mais** (34 sequências, 15 motoristas), para que todos os candidatos sejam comparados nas mesmas sequências. A MIL precisa de pelo menos 1 minuto de calibração e 1 minuto avaliado.

**Descrição extra, fora do critério:** o PERCLOS absoluto nas 87 sequências de 1 min ou mais, usando o minuto inteiro, sem calibração.

**Rótulo:** a classe da sequência (sonolenta ou não), dada por observadores, clipe a clipe. Todas as sequências têm uma classe só.

**Extração:**
- **Extrator:** o `ExtratorRosto` da demo, no quadro inteiro e em modo IMAGE, como no UTA (seção 8.5), com os 61 sinais e o YOLO da semente 42.
- **10 fps pelo tempo:** em cada clipe, toma-se o quadro mais próximo de cada múltiplo de 100 ms (os clipes estão a 25, 30 ou 60 fps), o que dá 100 amostras por clipe.
- **Clipes extraídos:** todos os 2.074, para que a base também possa servir a treinos futuros com validação por motorista.
- **Cache e licença:** a saída vai para `data/cache/sust_rico/`, fora do Git. Nenhuma imagem da SUST aparece no notebook nem no paper, porque a licença dos vídeos não está informada.
- **Tempo:** cerca de 207 mil amostras a cerca de 20 ms, o que dá de 1 a 1,5 h num processo ou cerca de 25 min em 4.
- **Checagem de qualidade, fixada agora:** o rosto precisa ser achado em pelo menos 90% das amostras das 34 sequências do critério. A taxa é reportada antes de qualquer resultado. Se não passar, a SUST não decide o critério, e isso é registrado.

**Nada é treinado, calibrado ou escolhido na SUST:**
- todos os modelos e padronizações vêm do UTA;
- a calibração do 1º minuto e a linha de base do adaptativo usam só os sinais do começo da própria sequência, sem rótulo, como a demo faria.

## Modelos na SUST

- **MIL-GRU-4:** os pesos da demo (`mil_gru4_uta.pt`), treinados no UTA inteiro com 12 épocas e 5 sementes.
- **MIL-Transformer-14:** não há pesos gravados, só previsões. Ele é retreinado no UTA inteiro do mesmo jeito da parte B da 8.7 (`prever_b`), com 10 épocas e as 5 sementes, e aplicado à SUST sem ajuste.
- **Padronização dos canais e dos atributos Δ:** a do UTA, como no DROZY.
- **O controle de pose (Δ pose média, logística treinada no UTA)** é reportado na SUST, como na 8.7. Se ele passar bem de 0,5, a normalização não tirou o efeito da sessão ou da câmera, e os resultados pedem cautela.

## Métricas e incerteza

- **Métrica principal:** AUC por sequência (ou vídeo), sem o minuto de calibração, com as redes na média das 5 sementes.
- **Intervalos:** bootstrap pareado por motorista (SUST) ou pessoa (UTA e DROZY), com 2.000 sorteios, usando `auc_ic` e `dif_auc_v` da seção 8.7 sem mudança.
- **Secundária:** a acurácia balanceada, com o limiar de maior acurácia no UTA (`limiar_acuracia`) nos sinais diretos e 0,5 nas redes.
- **Comparações reportadas,** em cada uma das 3 bases:

| Comparação | Papel |
|---|---|
| MIL-Transformer-14 − PERCLOS absoluto | Trava (3 bases), média e nível 2 (SUST) |
| PERCLOS combinado − PERCLOS absoluto | Trava (3 bases), média e nível 2 (SUST) |
| PERCLOS adaptativo − PERCLOS absoluto | Trava (3 bases), média e nível 2 (SUST) |
| MIL-GRU-4 − PERCLOS absoluto | Descrição |

A tabela final traz, para cada candidato, a AUC em cada base, a AUC média, a diferença média contra o PERCLOS absoluto com o IC estratificado e o resultado da trava.

**Descrições, fora do critério:**
- a distribuição de b e as calibrações recusadas em cada base;
- na SUST, a AUC dentro do motorista, com os 7 motoristas que têm as duas classes, como na seção 8.6;
- o DROZY só com os testes 2 e 3 (mesma iluminação), como na 8.7.

## Laya: exploratória e opcional

A Laya (classificador de opções da Convai sobre o ModernBERT-large, 421M parâmetros) **não entra no critério e não conta como candidato.**

- **Quando roda:** só se sobrar tempo, ou se o Antônio já tiver o ambiente pronto.
- **Entrada:** o mesmo que a Logística-Δ16 da 8.7, um JSON com a média dos 16 atributos Δ do vídeo.
- **Treino:** a versão leve, com o leitor congelado e só a cabeça treinada, nas mesmas dobras do UTA e com as mesmas 5 sementes.
- **Aplicação:** sem ajuste no DROZY e na SUST, com a ordem das opções fixa.
- **Comparação:** com a Logística-Δ16.
- **Peso na decisão:** o resultado entra no notebook marcado como exploratório e não muda o modelo final.

## Conferência da implementação

Antes de mostrar qualquer número novo:

1. **Os números da 8.7 batem:** PERCLOS absoluto 0,814 (UTA) e 0,619 (DROZY); MIL-GRU-4 0,742 e 0,708; MIL-Transformer 0,875 e 0,743; MIL-GRU-4 − PERCLOS absoluto −0,071 (de −0,144 a −0,004) no UTA.
2. **MIL-Transformer retreinado:** as previsões no DROZY repetem as de `data/cache/drozy_mil/`. Se a GPU ou a ordem das contas mudar algo, a diferença é registrada, e não corrigida.
3. **MIL-GRU-4 da demo:** as previsões no DROZY repetem as de `data/cache/drozy_mil/` (o `CLAUDE.md` diz que o `MonitorSonolencia` já reproduz a parte B).
4. **PERCLOS adaptativo com b = 0:** reproduz exatamente o PERCLOS absoluto.
5. **SUST:** a taxa de rosto achado é mostrada antes de qualquer AUC.

As tabelas são mostradas ao Rafael antes de qualquer mudança no texto, no resumo (seção 9), no `README.md` e no `CLAUDE.md`.

## Emenda de 13/11/2026: UL-DD como possível 4ª base

Aprovada pelo Rafael em 13/11/2026, **antes de ver qualquer número da SUST e antes de abrir os dados da UL-DD**. O acesso à UL-DD (CPSLab, University of Louisiana at Lafayette) foi liberado em 13/11, e o pacote liberado tem 11,8 GB. O conteúdo ainda não foi visto.

**Condições de entrada, todas até 14/11/2026 às 18h:**
1. **Conteúdo:** o pacote tem vídeo do rosto e KSS (ou um rótulo de alerta e sonolento por sessão) para pelo menos parte das pessoas.
2. **Qualidade:** a extração acha o rosto em pelo menos 90% das amostras usadas, a mesma regra da SUST.
3. **Rótulo fixado antes de qualquer resultado na base:** a proposta é sonolento = KSS ≥ 7, o mesmo corte do DROZY (Regulamento Delegado (UE) 2021/1341).

As condições dependem só do conteúdo da base e da qualidade da extração, e não de um resultado. Por isso a seção 12 pode rodar com a SUST antes de a UL-DD ficar pronta, e o que se vir na SUST não muda se a UL-DD entra.

**Se as três condições valerem, a UL-DD entra no critério:**
- **Nível 1:** a AUC média passa a ser sobre 4 bases (UTA, DROZY, SUST e UL-DD), cada uma com o mesmo peso. A trava passa a valer nas 4.
- **Nível 2:** para afirmar a superioridade, é preciso IC95% acima de zero na **média das diferenças nas duas bases novas** (SUST e UL-DD), com bootstrap por pessoa ou motorista dentro de cada base. Não basta IC acima de zero numa delas só, porque isso daria duas chances de acertar por sorte.

**Se alguma condição falhar,** a UL-DD vira um teste separado, com protocolo próprio, e não muda a escolha do modelo final. Isso é registrado.

**Antes de qualquer resultado na UL-DD, ficam registrados nesta emenda:** a unidade (sessão ou vídeo), a divisão em minutos, o minuto de calibração, a taxa de 10 fps e o método de extração (quadro inteiro ou o do DROZY). Eles só podem ser escolhidos olhando a estrutura da base e a checagem de viabilidade, sem rótulo.

**Detalhes da UL-DD, aprovados pelo Rafael em 13/11/2026.** Eles foram fixados olhando só a estrutura da base, a contagem dos rótulos e uma checagem de viabilidade sem rótulo (1 vídeo, 40 quadros), antes de qualquer resultado:

1. **Unidade:** a sessão de 40 min.
   - **Sessões usadas:** só as que têm vídeo infravermelho liberado. Pela planilha "Publicity" do `Info.xlsx`, são 29 sessões de 16 pessoas: 13 pessoas com as sessões alerta e sonolenta, e C, F e L só com a alerta. B, I e M não têm vídeo liberado. A lista é conferida com os arquivos baixados.
   - **Bootstrap:** por pessoa.
2. **Rótulo:** sonolenta quando a **mediana dos 10 KSS da sessão** (um a cada 4 min, `Labels.csv`) é **7 ou mais**. Isso dá 11 sessões sonolentas e 18 alertas. As sessões sonolentas de G (mediana 6,25) e O (6,5) ficam como alertas. O tipo de sessão (alerta ou sonolenta) entra só como descrição.
3. **Minutos:** a 10 fps, com o quadro mais próximo de cada múltiplo de 100 ms (1 a cada 6 quadros a 60 fps), cada sessão dá 40 minutos de 600 quadros. O 1º é o minuto de calibração, e os outros 39 entram nos modelos.
4. **Extração:** o método do DROZY (seção 8.7). O MediaPipe rastreia o rosto em modo de vídeo no quadro inteiro, o rosto é recortado e ampliado para 224×224 com cerca de 59 px entre os olhos, e roda a extração da seção 8.5 no recorte.
   - **Por que esse método:** o vídeo tem 240×220 e o olho tem cerca de 12 px, como no DROZY.
   - **Checagem de viabilidade:** o rosto foi achado em 40 de 40 quadros.
   - **Limitação:** diferente do DROZY, não há anotação dos olhos para conferir o recorte.
   - **Cache:** `data/cache/uldd_rico/`.
5. **Tempo:** cerca de 700 mil amostras, de 3 a 5 h em 4 processos. A extração começa quando o download e a extração da SUST terminarem.

**Acordo de uso:** só pesquisa acadêmica, com segurança física e eletrônica dos dados e citação de "A multimodal drowsiness dataset using video, biometric, and behavioral data". Os dados ficam só no disco do Rafael, em `data/bases_novas/ul_dd/`, fora do Git, sem ir para o Colab nem para o grupo. Nenhuma imagem aparece no notebook nem no paper até o acordo completo ser lido.

## Onde entra no notebook

Numa seção nova, **12. Modelo final de sonolência**. A seção 11 fica reservada para o modelo final de microssono, que espera a extração e os resultados do Antônio. As funções da seção 8.7 são reaproveitadas sem mudança.

## Riscos conhecidos

- **Pouca base:** 34 sequências de 15 motoristas, só 7 com as duas classes, e mediana de 2 minutos avaliados. O IC na SUST será largo, e o mais provável é que o nível 2 não confirme a superioridade.
- **A média favorece o que já se viu:** o critério de escolha mudou depois de ver o UTA e o DROZY. O AUC do Transformer no UTA vem da base em que ele foi desenvolvido e destacado, então tende a ser otimista e pesa um terço da média. Isso entra como limitação.
- **Bases muito diferentes na mesma média:** o UTA é gravado em casa, o DROZY é infravermelho em laboratório e a SUST é direção real. A média simples dá o mesmo peso a cada contexto, e não a cada pessoa.
- **Sequências de uma classe só:** a normalização pelo 1º minuto apaga o nível de sono de uma sequência sonolenta. É o custo já medido na 8.7, e a SUST vai cobrá-lo de novo.
- **Rótulo por observador, clipe a clipe:** é diferente do autorrelato do UTA e do KSS do DROZY. Ele mede o comportamento visível, que pode estar mais perto do que o PERCLOS mede.
- **Mudança de domínio:** celular na mão ou no painel, carro em movimento, luz do dia e vídeo vertical.
- **Sessão:** a mesma pessoa aparece com a mesma roupa nos dois estados, o que sugere o mesmo dia. Isso diminui, mas não tira, o efeito da câmera. O controle de pose mede o que sobra.
- **O MIL-Transformer foi destacado depois de ver a 8.7.** A SUST é o teste novo que a 8.7 pedia, e só ela pode confirmá-lo.
- **Agrupamento dos motoristas à mão:** se dois grupos forem a mesma pessoa, o bootstrap subestima a incerteza.

## Análise de erros na SUST-DDD (exploratória, seção 12.1)

Aprovada pelo Rafael em 13/11/2026, **depois de ver as tabelas do critério na SUST e antes de qualquer resultado na UL-DD**. Como a 8.6, ela é exploratória.

**Regras:**
- **Não muda o critério nem os candidatos.**
- **Hipótese para a UL-DD:** se a análise sugerir uma, ela é escrita antes de rodar a UL-DD e testada lá só como teste exploratório separado, sem mudar o modelo final.

**Lista fixada antes de olhar:**
1. **Entre e dentro do motorista:**
   - a AUC de cada candidato dentro de cada motorista com as duas classes;
   - quanto o PERCLOS sobe do alerta ao sonolento na mesma pessoa;
   - quanto o PERCLOS varia entre os motoristas, nas sequências alertas.
2. **Tamanho do olho:** o EAR de olho aberto de cada sequência e o acerto por terço desse EAR, separado por classe. O acerto é medido no PERCLOS absoluto e no combinado, com os limiares do UTA.
3. **Câmera e luz:** quanto o brilho (`continuidade.csv`), a pose média absoluta e a taxa de rosto separam as classes sozinhos, e o acerto por terço do brilho. A AUC de cada eixo da Δ pose, para ver de onde vem o controle de 0,639.
4. **Queda do MIL-Transformer:** a média e o desvio de cada um dos 14 canais e dos 16 atributos Δ, depois da normalização e da padronização do UTA, comparados entre UTA, DROZY e SUST.
5. **Duração:** o acerto de cada candidato por número de minutos avaliados (1, 2 e 3 ou mais).

## Hipóteses da 12.1 testadas na UL-DD (exploratórias)

Aprovadas pelo Rafael em 13/11/2026, **depois de ver a 12.1 e antes de qualquer modelo rodar na UL-DD** (até aqui, só a taxa de rosto da UL-DD foi calculada: 99,93%). Elas não mudam o critério nem o modelo final.

- **H1, duração:** na SUST, o acerto subiu com o número de minutos avaliados. Na UL-DD, recalculamos a AUC de cada candidato usando só os primeiros 1, 3, 10 e 39 minutos depois da calibração.
  - **O que se espera:** a AUC do PERCLOS combinado e das duas MILs sobe de 1 para 39 minutos.
  - **Como as redes rodam:** as treinadas só no UTA, sem ajuste, com o saco cortado nos primeiros k minutos.
- **H2, giro da cabeça:** na SUST, o desvio do yaw ficou 2,1 vezes o do UTA, e a hipótese é que isso derrubou o MIL-Transformer. Na UL-DD (simulador), medimos o desvio do yaw e do "desvio do yaw" em unidades do UTA, como no item 4 da 12.1.
  - **O que se espera:** os dois desvios ficam abaixo de 1,5.
  - **E também:** a diferença MIL-Transformer − PERCLOS absoluto na UL-DD fica acima da diferença na SUST (−0,143).
- **H3, olho pequeno:** na SUST, o EAR de olho aberto separou as classes sozinho (AUC 0,39).
  - **O que se mede na UL-DD:** a AUC do EAR de olho aberto sozinho (por sessão, mediana dos minutos avaliados); a AUC entre pessoas de cada candidato; e, nas pessoas com sessões das duas classes, a fração em que a sessão sonolenta recebe a nota maior (AUC dentro da pessoa).
  - **O que se espera:** a AUC dentro da pessoa fica bem acima da AUC entre pessoas.

## Exploratório: fine-tuning com a SUST, teste na UL-DD

Aprovado pelo Rafael em 13/11/2026, **antes de ver a análise de erros da 12.1 e antes de qualquer resultado na UL-DD**. Ele não muda o critério nem o modelo final, que foram fixados sem esse candidato.

**Pergunta:** treinar também com dados de direção real (SUST-DDD) ajuda as redes a generalizar para uma base nova?

**Desenho:**
- **Treino:** a MIL-GRU-4 e a MIL-Transformer-14 com os mesmos hiperparâmetros da parte B da 8.7, as mesmas épocas (12 e 10) e as mesmas 5 sementes, nas 118 sequências do UTA mais as 34 da SUST (2 min ou mais). As duas bases também entram juntas na padronização dos canais e dos atributos. A SUST usa a mesma normalização pelo 1º minuto.
- **Teste:** só na UL-DD, e só se ela passar nas condições da emenda.
- **Comparações (AUC por sessão, bootstrap pareado por pessoa, 2.000 sorteios):**
  - MIL-GRU-4 com SUST − MIL-GRU-4 só UTA;
  - MIL-Transformer-14 com SUST − MIL-Transformer-14 só UTA;
  - PERCLOS combinado com a GRU-4 nova − PERCLOS combinado original. A padronização do logit continua com a média e o desvio do UTA, das previsões da GRU-4 nova no UTA.
- **Leitura:** é um resultado exploratório. Se ajudar, ele entra no paper como resultado e como próximo passo, sem trocar o modelo final. A SUST deixa de ser teste para essas redes novas, mas continua teste para as originais.

## Exploratório futuro: calibrar na sessão alerta da mesma pessoa

Ideia do Rafael em 13/11/2026. Fica **fora do critério** e só roda depois dele, com protocolo próprio.

**A ideia:** como produto, o motorista grava alguns minutos descansado no primeiro uso, e o sistema compara as viagens seguintes com essa referência. É a "linha de base por pessoa" dos próximos passos do `CLAUDE.md`.

**Por que não entra no critério:**
- **Rótulo na entrada:** usar a sessão alerta como referência exige saber qual sessão é alerta. O protocolo da 8.7 já proíbe "usar o vídeo alerta para normalizar o sonolento".
- **Não há como calcular a AUC:** se a sessão alerta inteira vira referência, sobra só a sonolenta para avaliar.
- **Efeito de sessão:** dividir a sessão alerta compara um trecho da mesma gravação da referência com outra gravação. A diferença de câmera, luz e posição separaria as classes, como no UTA (seção 8.6).

**Desenho proposto para o teste futuro, na UL-DD:**
- **Pessoas:** as 13 que têm as duas sessões com vídeo.
- **Referência:** os primeiros 10 min da sessão alerta.
- **Teste:** o resto da sessão alerta contra a sessão sonolenta, com os candidatos deste protocolo normalizados pela referência.
- **Controle de sessão:** pose e brilho médios, para medir quanto da separação vem da gravação.
- **Leitura:** o resultado vale só como indício e entra no paper como trabalho futuro, com uma primeira medida. Ele não muda o modelo final.

## O que fica fora

- Mudar candidatos, definições (janela de 30 s, percentil 25, regra de recusa, padronização do combinado), sequências usadas, pesos da média ou regra de decisão depois de ver qualquer número da SUST ou dos candidatos novos.
- Treinar, ajustar ou escolher limiar na SUST.
- Re-treinar redes com validação cruzada na SUST. Isso fica para depois, com protocolo próprio, e não decide o modelo final.
- WACHsens, UL-DD e as gravações do grupo.
- Usar o que o Antônio vir na SUST para mudar qualquer coisa deste protocolo.
