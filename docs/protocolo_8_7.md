# Protocolo da seção 8.7: MIL com atenção sobre os minutos, com validação externa no DROZY

Escrito e aprovado pelo Rafael em 07/11/2026, **antes de qualquer treino e antes de extrair os sinais do DROZY**. O protocolo não muda depois disso. Qualquer teste fora dele entra no notebook marcado como exploratório.

O experimento tem duas partes:

| Parte | Base | Papel |
| --- | --- | --- |
| A | UTA-RLDD (as mesmas 60 pessoas das seções 8.3 a 8.6) | Desenvolvimento: treino e comparação com validação cruzada |
| B | DROZY (14 pessoas que nunca usamos) | Confirmação: os modelos da parte A, treinados no UTA inteiro, aplicados sem nenhum ajuste |

## Por que este experimento

A análise de erros (seção 8.6) mostrou três problemas do UTA-RLDD que nenhuma arquitetura das seções 8.4 e 8.5 resolveu:

1. **Variação entre pessoas:** o PERCLOS varia entre pessoas alertas tanto quanto do alerta ao sonolento.
2. **Rótulo fraco:** o rótulo vale para o vídeo inteiro, mas o acerto nos minutos sonolentos sobe de 54% no 1º minuto para 74% do 8º em diante.
3. **Sessão:** cada classe foi gravada num dia diferente, e a câmera de cada dia já separa as classes dentro da pessoa.

Este experimento ataca os três de uma vez, com duas mudanças:

- **Normalização pelo próprio vídeo.** Cada canal é medido em relação ao 1º minuto do mesmo vídeo, que vira um minuto de calibração e sai da avaliação. Isso tira o nível de cada pessoa e de cada sessão (olho pequeno, câmera do dia) e deixa só a mudança ao longo da gravação. A normalização não usa o rótulo, e no produto ela equivale a calibrar no começo da viagem.
- **MIL com atenção** (aprendizado de múltiplas instâncias; Ilse, Tomczak e Welling, 2018, [arXiv 1802.04712](https://arxiv.org/abs/1802.04712)). O vídeo é um "saco" de minutos com um único rótulo. A rede gera um vetor por minuto e aprende quanto cada minuto pesa na decisão do vídeo. Assim, os minutos do começo, que ainda parecem alertas, podem pesar menos.

**Por que a parte B:** a ideia saiu da seção 8.6, que olhou as previsões de teste, e a parte A é a terceira rodada de experimentos nas mesmas 60 pessoas. Um resultado positivo só na parte A pode refletir essas 60 pessoas, e não a sonolência. A parte B testa os mesmos modelos em pessoas, câmera e laboratório novos, e foi fixada antes de vermos qualquer resultado da parte A.

## Parte A: UTA-RLDD

### Dados

- **Base:** a extração da seção 8.5 (`data/cache/rldd_rico/`), só com os clipes completos (600 frames).
- **Unidade:** o vídeo (pessoa e classe). **A pessoa 42 sai:** ela não tem o vídeo sonolento, e o alerta tem só 1 minuto completo. Ficam 118 vídeos de 59 pessoas, cada uma com um vídeo alerta e um sonolento. Os vídeos têm de 4 a 18 minutos completos, com mediana de 9.
- **Minuto de calibração:** o 1º minuto (clipe 0) de cada vídeo serve só para a normalização. A rede, as linhas de base e as métricas usam do 2º minuto em diante (de 3 a 17 minutos por vídeo).
- **Dobras:** as mesmas 5 dobras por pessoa das seções 8.3 a 8.5. As duas gravações da pessoa ficam sempre na mesma dobra.

### Normalização pelo próprio vídeo

Para cada vídeo e cada canal contínuo, subtrai-se a mediana desse canal no minuto de calibração, contando só os frames com rosto. Depois, cada canal é padronizado com a média e o desvio do treino da dobra, como na seção 8.5. O canal "rosto encontrado" fica como está. A pose passa a ser relativa ao minuto de calibração, e não mais à mediana do próprio clipe, para que a cabeça caindo ao longo do vídeo apareça.

Os atributos por minuto (os 16 da seção 8.5) são normalizados da mesma forma: atributo do minuto menos o atributo do minuto de calibração. É o "Δ" das tabelas abaixo.

### Modelos

| Modelo | Entrada | Papel |
| --- | --- | --- |
| PERCLOS absoluto por vídeo | Média do PERCLOS dos minutos, sem normalização | Referência: o que a seção 8 daria por vídeo |
| **ΔPERCLOS por vídeo** | Média do ΔPERCLOS dos minutos | Linha de base simples com a mesma normalização |
| **Logística-Δ16** | Média dos 16 atributos Δ sobre os minutos | **Linha de base principal:** os mesmos sinais resumidos num modelo linear |
| **MIL-GRU-4 híbrida** | 4 canais por frame (P(fechado), EAR, boca, rosto), normalizados, mais os 16 atributos Δ do minuto | **Rede principal** |
| MIL-Transformer-14 híbrido | Os 14 canais da seção 8.5, normalizados, mais os 16 atributos Δ | Secundária (recomendação da organização) |
| GRU-4 híbrida com média | A mesma da principal, com média simples dos minutos no lugar da atenção | Secundária: mostra se a atenção faz diferença |
| Controle: Δ pose média | Média, sobre os minutos, da pose média do minuto menos a do minuto de calibração (logística) | Mede se a câmera ainda separa as classes depois da normalização |

**Arquitetura das redes MIL:**
- **Codificador de minuto:** GRU de 32 unidades (como a da seção 8.4) ou o transformer da seção 8.5, com dimensão 32, 2 camadas e 4 cabeças. Ele lê os 600 frames do minuto e devolve um vetor.
- **Vetor do minuto:** a saída do codificador, concatenada aos 16 atributos Δ do minuto e passada por uma camada linear para 32 dimensões.
- **Atenção com porta (Ilse et al.):** com camada interna de 16 e dropout de 0,2, dá um peso por minuto, com soma 1 no vídeo. O vetor do vídeo é a média ponderada dos minutos.
- **Saída:** uma camada linear dá um logit por vídeo.

**Treino:**
- **Lotes e otimizador:** lotes de 8 vídeos, AdamW com taxa de 1e-3 e weight decay de 1e-3, até 60 épocas, com paciência de 10.
- **Validação:** 20% das pessoas do treino da dobra, e guarda-se a época com menor perda.
- **Aumento de dados:** a cada vídeo sorteia-se um sub-saco com 60% a 100% dos minutos. Em cada minuto, uma janela aleatória de 54 s e um ruído de 0,05 nos canais contínuos, como na seção 8.4.
- **Teste:** usa todos os minutos (do 2º em diante), inteiros.
- **Sementes:** 5 (42, 1, 2, 3 e 4).

**Linhas de base:** a logística é a da seção 8.3 (imputação pela mediana, padronização e `LogisticRegression` padrão), treinada por vídeo. No ΔPERCLOS e no PERCLOS absoluto, a AUC usa o valor direto. A acurácia usa o limiar de maior acurácia no treino da dobra.

### Métricas da parte A

- **Métrica principal:** AUC por vídeo, com os 118 vídeos e previsões fora da dobra.
- **Métrica secundária:** acurácia balanceada por vídeo, com limiar de 0,5 nas logísticas e nas redes.
- **Comparação:** bootstrap pareado por pessoa (2.000 sorteios), como na seção 8.4. As redes entram com a média das AUC das 5 sementes.
- **Também reportados:** a rede principal contra o ΔPERCLOS e contra o PERCLOS absoluto, e o ΔPERCLOS contra o PERCLOS absoluto. Este último mostra quanto a normalização custa ou ajuda.
- **Controle:** se a Δ pose média passar bem de 0,5, a normalização não removeu o efeito da sessão, e os resultados devem ser lidos com cautela.
- **Atenção (descritivo):** o peso médio da atenção por posição do minuto, separado por classe, na rede principal. A hipótese é que, nos vídeos sonolentos, os minutos finais pesem mais. Isso é só descrição, não critério.

## Parte B: DROZY

### A base

DROZY (Massoz, Langohr, François e Verly, WACV 2016), baixado do repositório ORBi da Universidade de Liège em 07/11/2026, em `data/drozy/` (fora do Git).

- **Pessoas e testes:** 14 pessoas. Cada uma fez 3 testes de vigilância (PVT) de 10 minutos: PVT1 às 10h, descansada; PVT2 às 3h30, depois de cerca de 18 h acordada; PVT3 ao meio-dia seguinte, com 28 a 30 h acordada. O KSS (escala de sonolência de Karolinska, de 1 a 9) foi anotado logo antes de cada teste.
- **Vídeos:** 36 de 42 (5 se perderam, e o 7-1 não aconteceu), todos com 10 minutos, 12 por teste.
- **Câmera:** uma câmera infravermelha (Kinect v2) a cerca de 0,7 m, em 512×424, na mesma sala para todos os testes.
- **Taxa de quadros:** os vídeos estão a 30 fps, exceto os testes 2 e 3 das pessoas 1 a 8, que estão a cerca de 15 fps.
- **Iluminação:** a luz da sala foi apagada nos testes 2 e 3.
- **Licença:** permite pesquisa e avaliação, mas não uso comercial. Ela proíbe redistribuir a base ou parte dela e mostrar as imagens, salvo as marcadas como publicáveis, e exige citar o artigo do WACV 2016. **Por isso, nenhum frame do DROZY aparece no notebook nem no paper.**

### Rótulo

**Sonolento = KSS ≥ 7.** O corte segue a regulação europeia de sistemas de aviso de sonolência (Regulamento Delegado (UE) 2021/1341, Anexo I, 3.3.1): o sistema *pode* avisar no KSS 7 e *deve* avisar no KSS 8 ou mais. KSS 7 significa "com sono, mas sem esforço para ficar acordado". O rótulo vale para o vídeo inteiro, como no UTA.

Contagem, feita só com o rótulo e antes de qualquer modelo:
- 15 vídeos sonolentos e 21 alertas;
- 11 das 14 pessoas têm as duas classes;
- todos os vídeos do teste 1 são alertas (KSS de 2 a 6).

### Extração

A mesma da seção 8.5 (6 canais, pose e 52 blendshapes; P(fechado) com o YOLO da semente 42), com três ajustes para a câmera do DROZY. Eles foram escolhidos numa checagem de viabilidade que não usou o rótulo:

1. **10 fps:** em cada vídeo, toma-se o frame mais próximo de cada múltiplo de 100 ms, pelos tempos do arquivo `timestamps`, como no UTA.
2. **Rosto pequeno:** no DROZY, o olho tem cerca de 10 px de largura. Por isso o rosto é localizado em duas etapas:
   - o MediaPipe em modo de vídeo, que rastreia o rosto de um frame para o outro, com confiança mínima de 0,2, acha o rosto no quadro inteiro;
   - o rosto é recortado num quadrado e ampliado para 224×224, com a escala ajustada para que a distância entre os olhos fique perto da do UTA (cerca de 59 px);
   - a extração da seção 8.5 roda sobre esse recorte.

   Na checagem de viabilidade (5 vídeos, 2 min cada), o rosto foi achado em 100% dos frames. O centro do olho ficou a 3–7% da distância entre os olhos das anotações do próprio DROZY. Sem esse ajuste, o MediaPipe achava o rosto em só 2% a 37% dos frames de alguns vídeos.
3. **Divisão em minutos:** os 10 minutos viram 10 minutos de 600 frames. O 1º é o minuto de calibração, e os outros 9 entram nos modelos.

O vídeo continua infravermelho. O YOLO foi treinado no MRL Eye, que também é infravermelho, mas a imagem do DROZY é ampliada cerca de 1,7 vez e pode ficar borrada. Isso é um risco, e não há como medi-lo sem rótulo por frame.

### Modelos e treino

Todos os modelos da parte A são retreinados no UTA inteiro: 118 vídeos e as mesmas 5 sementes. Os hiperparâmetros são os da parte A, e as épocas são fixadas na mediana das melhores épocas da validação da parte A. Depois, os modelos são aplicados ao DROZY sem nenhum ajuste. A padronização dos canais usa a média e o desvio do UTA. Os limiares de acurácia também vêm do UTA.

### Métricas da parte B

- **Métrica principal:** AUC por vídeo nos 36 vídeos, com bootstrap pareado por pessoa (2.000 sorteios) e a média das 5 sementes nas redes.
- **Análise com a mesma iluminação:** a mesma AUC só nos testes 2 e 3 (24 vídeos), em que a luz estava apagada. Isso separa o sono da troca de iluminação entre o teste 1 e os outros.
- **Controle:** a Δ pose média, como na parte A.
- **Também reportados:** os mesmos pares da parte A e a acurácia balanceada.

## Critério do deep learning

O critério compara a rede principal (MIL-GRU-4 híbrida) com a Logística-Δ16 e é decidido antes de qualquer resultado:

| Resultado | Leitura |
| --- | --- |
| Parte A com IC95% da diferença de AUC acima de zero **e** parte B com diferença positiva | **Deep learning justificado, com confirmação externa** |
| Parte A com IC acima de zero, e parte B com diferença zero ou negativa | Ganho não confirmado fora do UTA. Não conta como justificado |
| Parte A sem IC acima de zero | Não justificado. A parte B é reportada como descrição |

Na parte B, só a direção da diferença é exigida, e não o intervalo. Com 36 vídeos de 14 pessoas, o intervalo será largo demais para excluir o zero, mesmo com um efeito real. O intervalo da parte B é reportado de qualquer forma. As redes secundárias são reportadas com o próprio intervalo, mas não decidem o critério.

## Riscos conhecidos

- **Poucos dados:**
  - na parte A, são 118 vídeos, e cerca de 95 no treino de cada dobra;
  - na parte B, são 36 vídeos de 14 pessoas.
- **A normalização pode tirar sinal:** se a pessoa já começa o vídeo sonolenta, o minuto de calibração também é sonolento. Isso é provável no DROZY, porque os testes 2 e 3 começam depois de 18 a 30 h sem dormir. A comparação do ΔPERCLOS com o PERCLOS absoluto mede esse custo nas duas bases.
- **Mudança de domínio na parte B:**
  - a imagem é infravermelha, e não colorida;
  - o rosto é ampliado;
  - a tarefa é um teste de reação na frente da tela, e não uma gravação livre;
  - os testes 2 e 3 têm iluminação diferente.
- **Rótulo autorrelatado nas duas bases:** o KSS é subjetivo, e as pessoas tendem a avaliar melhor a própria sonolência quando ela é alta do que quando é média, como diz o próprio artigo do DROZY.
- **Comparação com as seções 8.3 a 8.5:** a avaliação aqui é por vídeo e sem o 1º minuto, então os números não são diretamente comparáveis aos da AUC por clipe.

## O que fica fora

- Ajustar canais, normalização, arquitetura ou hiperparâmetros olhando as dobras de teste da parte A ou qualquer resultado da parte B.
- Treinar, calibrar ou escolher limiar no DROZY.
- Trocar a métrica principal, a rede principal, o corte do KSS ou o critério depois de ver os resultados.
- Usar o vídeo alerta para normalizar o sonolento (ou vice-versa). Isso poria o rótulo na entrada.
- Os dados de Massoz et al. (2018), que trazem só sinais e não imagens, e as medidas do PVT e da polissonografia do DROZY.
