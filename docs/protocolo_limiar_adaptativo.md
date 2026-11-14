# Protocolo da frente C: limiar adaptativo e condição 2 do critério de microssono

Escrito em 13/11/2026, **antes de calcular qualquer limiar adaptativo e antes de medir alarmes no Eyeblink8 ou no Drive&Act, e antes de rodar a fusão na classe alerta do UTA-RLDD**. Ele só vale depois de aprovado pelo Rafael e não muda depois disso. Qualquer conta fora dele entra no notebook marcada como exploratória.

## Por que este protocolo

Na apresentação intermediária (12/11), a banca pediu um limiar adaptativo. O projeto já tinha o motivo medido: na classe alerta do UTA-RLDD, a regra da demo dá 6,7 alarmes por hora, mas 5 das 60 pessoas somam 97% deles, e as 3 primeiras têm o olho aberto menor na imagem (EAR de olho aberto de 0,19 a 0,20, contra 0,25 da mediana, seção 8.2). Um limiar único pune quem tem o olho pequeno na imagem, seja pela anatomia, pelo ângulo da câmera ou pelo olhar.

Na mesma rodada, este protocolo mede a **condição 2 do critério da seção 10.4** para a fusão EAR + YOLO pela média, que já passou na condição 1.

## O que já se sabe antes deste protocolo

- Os números do FL3D com limiar fixo já foram vistos: YOLO com filtro (143,2 de 165 episódios de 1 s ou mais, 10,2 falsos alarmes, F2 0,880) e fusão pela média com filtro (149,6 de 165, 6,0, F2 0,917; F2 +0,037, de +0,010 a +0,071).
- A taxa de alarmes do YOLO da semente 42 na classe alerta do UTA já foi vista (64 alarmes em 9,5 h, seção 8.2), assim como quem dá esses alarmes.
- **Ainda não foram vistos:** nenhum número de limiar adaptativo, os alarmes da fusão no UTA e qualquer alarme no Eyeblink8 ou no Drive&Act.
- **Checagem de viabilidade feita antes de escrever (13/11), sem medir alarmes:** em 40 quadros de 2 vídeos do Eyeblink8, o MediaPipe achou o rosto em todos, com olho de 24 a 26 px de largura. No Drive&Act (câmera da coluna A, infravermelho próximo, 1280×1024), o rosto apareceu em 5% a 30% dos quadros no modo da seção 2 e em 15% a 63% de 2 minutos de 3 vídeos com o método do DROZY (rastreio em modo de vídeo e recorte ampliado, seção 8.7), com olho de 9 a 18 px. Ver "Bases de teste".
- **A fusão já é meio adaptativa.** O EAR entra na fusão como `fech_ear = 1 − EAR / referência`, com a referência do próprio vídeo (seção 2.1). Só o P(fechado) do YOLO é absoluto. Por isso, a versão adaptativa da fusão muda só a parte do YOLO.

## Como o limiar se adapta à pessoa

A ideia é a mesma da referência do EAR (seção 2.1): medir o olho aberto da própria pessoa no começo do uso e descontar essa linha de base.

1. **Janela de calibração:** os primeiros **30 s** de cada sequência, só com os quadros em que o rosto foi achado. São os mesmos 30 s da seção 2.1. Não usamos 60 s porque muitos vídeos do FL3D têm de 20 s a 2 min, e a janela cobriria o vídeo inteiro. Na demo, os 30 s cabem dentro da calibração do 1º minuto que ela já faz.
2. **Linha de base do YOLO:** b = **percentil 25** do P(fechado) na janela. É o espelho do percentil 75 do EAR: o EAR é alto com o olho aberto, e o P(fechado) é baixo, então os dois pegam o "quartil mais aberto" do começo.
3. **Sinal adaptativo:** `fech_yolo_adapt = clip((P − b) / (1 − b), 0, 1)`. A linha de base vira 0, e o olho fechado continua em 1. Na prática, o limiar efetivo da pessoa sobe de L para b + L·(1 − b). Quem tem o olho aberto bem classificado (b perto de 0) fica com o limiar de hoje.
4. **Fusão adaptativa:** a média de `fech_ear` (sem mudança) e `fech_yolo_adapt`.
5. **Limiar de olho:** continua escolhido pelo F1 (decisão de 13/11), do mesmo jeito que hoje, só que sobre o sinal adaptativo: no FL3D, o de cada vídeo vem dos outros 43 (`deixar_um_video_de_fora`), e o das bases de teste vem dos 39 vídeos de calibração (`limiar_na_calibracao`). A grade de limiares é a de hoje (`GRADE_LIMIAR`).
6. **Mesma convenção da seção 2.1 no tempo:** a linha de base dos 30 s é aplicada à sequência inteira, inclusive aos próprios 30 s. Ao vivo, nesses 30 s a demo ainda não teria a linha de base. Mantemos a convenção para que a fusão adaptativa seja comparável com a fusão aprovada, que já usa o EAR assim. Nas bases de teste, as sequências têm de 3 a 10 min, então o efeito é pequeno. Isso entra como limitação.

### E se a pessoa já começar sonolenta?

- **O percentil 25 tolera fechamentos no começo:** a linha de base só sobe se o olho estiver fechado em mais de 75% dos quadros com rosto da janela.
- **Calibração recusada:** se a janela tiver menos de 5 s com rosto, ou se b > 0,5 (o olho parece mais fechado do que aberto), a calibração é recusada e a sequência usa b = 0, ou seja, o limiar fixo de hoje. O número de sequências com calibração recusada é reportado em cada base.
- **O risco que sobra é a pálpebra pesada sem fechar:** quem começa sonolento com o olho meio caído, mas aberto, ganha um b mais alto e um limiar efetivo mais alto, e o sistema pode perder microssonos dessa pessoa. É o mesmo custo da normalização pelo 1º minuto na seção 8.7. **O FL3D mede esse custo diretamente,** porque os vídeos são de pessoas sonolentas, alguns começando já com microssono: se a adaptação perder microssonos, o recall e o F2 da validação cruzada caem. Também reportamos a taxa de alarmes na classe **sonolenta** do UTA, só como descrição (lá os alarmes não são necessariamente falsos), para ver quanto a adaptação silencia em pessoas com sono.
- **O EAR não muda.** A referência do EAR continua a da seção 2.1, sem a regra de recusa, porque ela faz parte da fusão já aprovada.

## Candidatos

Todos com T = 1 s e o filtro de bocejo congelado (seção 6.1), sem o piso de 3 s (que é a frente D).

| Sigla | Candidato | Limiar |
|---|---|---|
| Y | YOLO com filtro (sistema atual) | Fixo |
| F | Fusão pela média com filtro (seção 6.3) | Fixo |
| Y-A | YOLO adaptativo com filtro | Fixo sobre o sinal adaptativo |
| F-A | Fusão pela média adaptativa com filtro | Fixo sobre o sinal adaptativo |

**Sementes:** no FL3D, as 5 sementes do YOLO, com as contagens por vídeo na média das sementes, como nas seções 6.1 e 6.3. Nas bases de teste, só a **semente 42**, que é a do cache do UTA (seção 8) e a da demo. Os limiares da semente 42 escolhidos na calibração são 0,40 para Y (o `LIM_REGRA` da seção 8.2) e 0,35 para F (seção 6.3). Os de Y-A e F-A saem da mesma conta.

## Papel de cada base

| Base | Papel | O que se mede |
|---|---|---|
| FL3D, 44 vídeos (validação cruzada por vídeo) | Escolher limiares e medir o F2 (condição 1) | Recall de 1 s ou mais, falsos alarmes, precisão, F1 e F2 |
| FL3D, 5 vídeos de holdout | Confirmação fraca, só descrição | Os mesmos, com o limiar da calibração |
| Classe alerta do UTA-RLDD (60 pessoas, 9,5 h) | Só teste de alarmes falsos | Alarmes por hora |
| Eyeblink8 (8 vídeos, 4 pessoas, 0,66 h) | Só teste de alarmes falsos | Alarmes por hora |
| Drive&Act (15 pessoas, 11,4 h) | Só teste de alarmes falsos, **se passar na checagem de qualidade** | Alarmes por hora |

**Nas bases de teste, nada é treinado, calibrado ou escolhido.** Os limiares, a janela de 30 s, o percentil 25, a regra de recusa, o filtro, o T e a taxa de 10 fps ficam fixos antes de rodar. Todo alarme nessas bases conta como falso, porque as pessoas estão acordadas e nenhuma delas marca microssono.

**As gravações do Antônio não entram neste protocolo.** E nada do que alguém do grupo vir nas bases de teste (inclusive nos testes que o Antônio estiver fazendo nelas) pode orientar mudanças nos candidatos. Uma ideia que surgir de olhar essas bases vira um protocolo novo, e o teste dela precisa de outra base.

## Bases de teste: extração e checagem de qualidade

**Regra de entrada, fixada agora:** uma base de teste só entra na condição 2 se o rosto for achado em **pelo menos 90% das amostras de 10 fps da base inteira**. O motivo é que um quadro sem rosto nunca conta como olho fechado: com o rosto perdido muitas vezes, a base daria poucos alarmes por falta de sinal, e não porque o sistema acerta. Como referência, o UTA e o DROZY ficaram em 99,9% e 99,8%.

| Base | Extração | Tempo estimado (RTX 3050) | Situação |
|---|---|---|---|
| Classe alerta do UTA | Já está em `data/cache/rldd/` (P(fechado) da semente 42, EAR e boca, 10 fps) | Nenhum | Pronta |
| Eyeblink8 | `ExtratorRosto` da demo no quadro inteiro (modo IMAGE, como no UTA), 10 fps (1 de cada 3 quadros), cache em `data/cache/eyeblink8/` | Cerca de 24 mil amostras a 20 a 40 ms: 10 a 20 min num processo | Cabe |
| Drive&Act | Método do DROZY (seção 8.7): rastreio em modo de vídeo e recorte ampliado, 10 fps, cache em `data/cache/driveandact/` | Cerca de 410 mil amostras a 20 a 30 ms: cerca de 3 h num processo, ou 1 h em 4 | Cabe no tempo, mas a checagem de viabilidade (15% a 63% de rosto) indica que não passa na regra de entrada |

- **10 fps em todas as bases de teste,** como no UTA, que já está a 10 fps. Os parâmetros da regra em quadros a 25 fps são convertidos pelo tempo com `em_rldd`, como na seção 8.2: juntar trechos fechados separados por 0,12 s vira 1 quadro, e a margem do bocejo vira 10 quadros.
- **Drive&Act:** a proposta é **não rodar a extração completa** e registrar a base como fora da condição 2, com o motivo: a câmera da coluna A vê o rosto de lado e pequeno, e o rosto some em boa parte do tempo. Se o grupo preferir rodar mesmo assim, a regra de 90% decide sobre a base inteira, e o número só é olhado depois de a taxa de rosto ser conferida. A base continua útil para a frente E (olhar para baixo e celular), com outro método.
- **Pelo critério da 10.4,** se uma base não couber, o critério vale com as que ficarem, e isso é registrado no notebook e no paper.
- **Licenças:** no Eyeblink8 (GPL3), nenhuma imagem é necessária. No Drive&Act, nenhuma imagem é mostrada. Nada das bases é versionado.

## Métricas

**FL3D (validação cruzada e holdout):** as mesmas da frente B (`docs/protocolo_metricas_f.md`), sem mudança: recall nos episódios de 1 s ou mais, falsos alarmes (em bocejo e fora), precisão por alarme, F1 e F2 (β = 2).

**Bases de teste,** cada base separada e a soma:

- alarmes, horas e **alarmes por hora**;
- pessoas (ou vídeos) sem nenhum alarme e a fração dos alarmes que vêm das 5 pessoas com mais alarmes;
- **soma das bases:** total de alarmes ÷ total de horas, como a 10.4 define. A soma pesa cada base pelo tempo de vídeo.

**Unidade de cada base:** no UTA, a pessoa (sequência emendada da classe alerta, como na seção 8.2). No Eyeblink8, o vídeo, porque a base não diz qual vídeo é de qual pessoa. No Drive&Act, se entrar, a pessoa (as 2 sessões emendadas).

**Descrições pedidas pela banca, sem entrar no critério:**

- **Viés do olho pequeno (classe alerta do UTA):** alarmes por hora de cada candidato por terço do EAR de olho aberto da pessoa (o mesmo atributo da seção 8.2), e os alarmes das 5 pessoas que mais alarmavam com Y.
- **Linha de base b:** distribuição de b em cada base e o número de calibrações recusadas.
- **Custo em quem tem sono:** alarmes por hora de cada candidato na classe sonolenta do UTA.

## Incerteza e comparações

- **FL3D:** bootstrap por vídeo, pareado, 5.000 sorteios, semente `SEMENTE`, IC95% pelos percentis 2,5 e 97,5, com `diferenca_pareada` (seção 6.1) sem mudança.
- **Bases de teste:** bootstrap pareado pela unidade de cada base (pessoa ou vídeo), 5.000 sorteios, semente `SEMENTE`. Na soma, o sorteio é feito dentro de cada base (estratificado), e a taxa somada sai de cada sorteio.
- **Comparações reportadas (a − b), fixadas agora:**

| Comparação | FL3D: F2 (e F1, recall e falsos) | Bases de teste: alarmes por hora |
|---|---|---|
| F − Y | Já reportada (frente B) | Sim: é a condição 2 da fusão |
| Y-A − Y | Sim | Sim |
| F-A − F | Sim | Sim |
| Desafiante adaptativo − vencedor da etapa 1 | Sim | Sim |

- **Leitura:** uma diferença só conta como conclusiva se o IC95% não incluir zero, como em todo o notebook. Não acrescentamos comparações depois de ver os números.

## Como o critério da 10.4 é aplicado

Em duas etapas, "sempre contra o vencedor do momento", como a 10.4 diz:

1. **Etapa 1, F contra Y.** A condição 1 já passou (+0,037, de +0,010 a +0,071). A condição 2 é medida aqui: F passa se a taxa somada de F não for maior que a de Y. Se passar, F é o vencedor da etapa 1. Senão, Y continua.
2. **Etapa 2, adaptativo contra o vencedor.** O **desafiante** é o candidato adaptativo (Y-A ou F-A) com o maior F2 na validação cruzada do FL3D. Ele vira o sistema final se (1) a diferença de F2 contra o vencedor da etapa 1 tiver IC95% sem zero e (2) a taxa somada dele não for maior que a do vencedor. Se o desafiante não passar, o outro candidato adaptativo **não** é testado no lugar dele, para não multiplicar tentativas. Os dois são reportados de qualquer jeito.

- **Condição 2 pelo valor pontual,** como a 10.4 aprovou ("não for maior"). Empate passa. O IC da diferença é reportado só para informação. Com poucos alarmes, o valor pontual é instável, e isso entra como limitação.
- **Mesmo que nenhum adaptativo vire o sistema final,** o efeito dele no viés do olho pequeno é reportado como resultado. É a pergunta da banca, e ela tem resposta mesmo sem troca de sistema.

## Conferência da implementação

Antes de mostrar qualquer número novo ou mexer em texto:

1. **Números de hoje no FL3D,** com filtro, na validação cruzada: Y 143,2 de 165 com 10,2 falsos e F2 0,880; F 149,6 com 6,0 e F2 0,917; F − Y em F2 +0,037 (de +0,010 a +0,071). Limiares da semente 42 na calibração: 0,40 (Y) e 0,35 (F).
2. **UTA, classe alerta, Y da semente 42 sem o piso:** os mesmos 64 alarmes em 9,527 h da seção 8.2 (lá o piso deu 0 alarme na classe alerta).
3. **Com b = 0 em todas as sequências,** Y-A e F-A reproduzem exatamente Y e F.
4. **Eyeblink8:** taxa de rosto achado reportada antes de qualquer alarme.

Se a execução for numa GPU diferente da RTX 3050 do Rafael, os números do YOLO podem mudar um pouco, e as diferenças são registradas, e não corrigidas.

## Onde entra no notebook

Numa subseção nova, **10.6 Limiar adaptativo e alarmes nas bases de teste (frente C)**, depois da 10.5, porque precisa dos sinais do FL3D (seção 6) e do cache do UTA (seção 8). As funções de avaliação das seções 2 a 6 não mudam. As tabelas são mostradas ao Rafael antes de qualquer mudança no texto, no resumo (seção 9), no `README.md` e no `CLAUDE.md`.

## Cronograma até 15/11

| Passo | Tempo |
|---|---|
| Implementar a 10.6 e conferir os números de hoje | 1 a 2 h |
| Extrair o Eyeblink8 | 10 a 20 min |
| Rodar as avaliações (FL3D, UTA, Eyeblink8) | Minutos |
| Execução completa do notebook | Cerca de 20 min, mais a extração nova |

## Riscos conhecidos

- **O UTA mostrou o viés que motivou a frente C,** então o ganho do adaptativo nele tende a sair otimista (seção 10.3). O Eyeblink8 é a base que não participou de nenhuma escolha.
- **Bases de teste pequenas em alarmes:** com Y, o UTA deu 64 alarmes, 40 de uma pessoa só. O Eyeblink8 tem 0,66 h e 8 vídeos. Poucos alarmes mudam a taxa.
- **Só a semente 42 nas bases de teste,** e o P(fechado) do UTA veio da extração no Mac (seção 8), enquanto o Eyeblink8 é extraído no Windows. A comparação entre candidatos é pareada dentro de cada base, então isso afeta os dois lados igualmente.
- **Nenhuma base de teste mede o recall.** Elas só têm pessoas acordadas. O custo da adaptação em microssonos só é medido no FL3D, que tem poucos motoristas e vídeos curtos.
- **A janela de 30 s olha um pouco para a frente** (convenção da seção 2.1).
- **O Drive&Act, se ficar de fora,** deixa a condição 2 sem nenhuma base de direção, nem simulada.

## O que fica fora

- Mudar a janela de 30 s, o percentil 25, a regra de recusa, o limiar de 90% de rosto, a taxa de 10 fps, o filtro, o T ou os limiares depois de ver qualquer número.
- Escolher o limiar pelo F2 ou ajustar qualquer coisa nas bases de teste.
- Adaptar também o EAR, o filtro de bocejo ou o T à pessoa.
- Outras bases (BINUS, SUST-DDD, gravações do grupo). A BINUS mediria o recall fora do FL3D e fica para um protocolo próprio.
- O piso de 3 s (frente D).
