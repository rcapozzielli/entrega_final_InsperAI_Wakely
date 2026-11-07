# Protocolo da seção 8.5: mais sinais do rosto

Escrito e aprovado pelo Rafael em 07/11/2026, **antes de qualquer treino**. O protocolo não muda depois disso. Qualquer teste fora dele entra no notebook marcado como exploratório. Os resultados estão na seção 8.5 do `wakely.ipynb`.

## Pergunta

A seção 8 mostrou que, com 4 sinais do olho e da boca, a GRU e a TCN não superam o PERCLOS (AUC de 0,750 e 0,754, contra 0,774). Aqui testamos duas coisas:

1. Sinais do rosto além do olho (posição da cabeça e expressões) melhoram a detecção de sonolência em 1 minuto?
2. Com esses sinais, uma rede (GRU, TCN ou transformer) aproveita melhor que um modelo linear com os mesmos sinais resumidos?

A pergunta 2 decide se o deep learning se justifica na etapa de sonolência. Se a rede e a logística melhorarem por igual, o ganho veio dos sinais, e não da rede.

## Dados

- UTA-RLDD recortado, pasta `len60`, os mesmos 1.126 clipes completos da seção 8 (600 frames).
- **Extração nova numa máquina só** (RTX 3050 do Rafael, Windows), com o YOLO da semente 42, em `data/cache/rldd_rico/`. A extração refaz os 6 canais da seção 8, além da pose e dos 52 blendshapes, porque o MediaPipe dá resultados um pouco diferentes em Mac e em Windows. Na pessoa 01, os canais antigos batem com o cache da Luana (correlação de 0,988 a 1,000).
- **As linhas de base da seção 8 são recalculadas na extração nova,** para que todos os modelos usem os mesmos dados. Os números originais da seção 8 ficam como estão.
- As mesmas 5 dobras por pessoa (`GroupKFold`) da seção 8, com os clipes na mesma ordem (juntados por pessoa, classe e clipe).

## Canais por frame (14)

Escolhidos pelo significado, antes de olhar qualquer diferença entre alerta e sonolento. Nos blendshapes, os lados esquerdo e direito viram a média.

| Grupo | Canais | Por quê |
| --- | --- | --- |
| Seção 8 (4) | P(fechado), EAR, abertura da boca, rosto encontrado | Os mesmos da seção 8.4 |
| Cabeça (3) | pitch, yaw e roll, **menos a mediana do próprio clipe** | Cabeceio e cabeça caindo. A posição absoluta depende de onde estava a câmera (a média do pitch vai de -37° a +10° entre pessoas), então só o movimento entra |
| Olhos (3) | eyeBlink, eyeSquint, eyeLookDown | Olho semicerrado e olhar caindo |
| Sobrancelhas (3) | browDown, browOuterUp, browInnerUp | Hipótese: quem luta contra o sono ergue as sobrancelhas para manter o olho aberto. Ainda falta uma fonte para isso |
| Boca (1) | jawOpen | Bocejo |

Os 52 blendshapes ficam guardados no cache, mas só esses 7 grupos entram nos modelos.

## Atributos por minuto (16)

- Os 6 da seção 8: PERCLOS, piscadas, duração mediana, fechamentos de 1 s ou mais, bocejos e EAR médio.
- 10 novos: desvio do pitch, do yaw e do roll no minuto, e a média de cada um dos 7 blendshapes.

## Modelos

Todos nas mesmas dobras, com previsões fora da dobra.

| Modelo | Entrada | Papel |
| --- | --- | --- |
| PERCLOS com limiar | PERCLOS | Linha de base da seção 8 |
| Logística-6 | 6 atributos da seção 8 | Linha de base da seção 8 |
| **Logística-16** | 16 atributos | **Linha de base principal:** os mesmos sinais novos, num modelo linear |
| GRU-4 | 4 canais da seção 8 | Separa o efeito da extração nova do efeito dos sinais novos |
| GRU-14 híbrida | 14 canais + 16 atributos | Rede com entrada rica |
| TCN-14 híbrida | 14 canais + 16 atributos | Rede com entrada rica |
| Transformer-14 híbrido | 14 canais + 16 atributos | Recomendação da organização |
| Controle de atalho | média absoluta de pitch, yaw e roll (logística) | Mede se a posição da câmera, que muda com o dia da gravação, já separa as classes |

**Entrada híbrida:** os 16 atributos, padronizados com o treino da dobra, são concatenados à saída da rede antes da camada linear final.

**Arquiteturas e treino:** a GRU e a TCN são as da seção 8.4, só com mais canais de entrada. O transformer divide o minuto em 60 pedaços de 1 s (10 frames), com projeção linear para 32 dimensões, posição aprendida, 2 camadas, 4 cabeças, camada interna de 64, dropout de 0,1 e média sobre os pedaços. O treino é o da seção 8.4: AdamW, até 40 épocas, paciência de 8, lote de 64, 20% das pessoas do treino como validação, janela aleatória de 54 s e ruído de 0,05. A taxa de aprendizado é 3e-3 na GRU e na TCN, como na seção 8.4, e 1e-3 no transformer. São 5 sementes (42, 1, 2, 3 e 4) e nenhum ajuste depois de ver as dobras de teste.

## Métricas e critério

- **Métrica principal:** AUC por clipe. As secundárias são a acurácia por clipe e por vídeo.
- **Comparação:** bootstrap pareado por pessoa (2.000 sorteios), como na seção 8.4.
- **Pergunta 1** (os sinais ajudam): Logística-16 contra Logística-6, e GRU-14 contra GRU-4.
- **Pergunta 2** (a rede ajuda): a melhor rede de 14 canais contra a Logística-16. **O deep learning se justifica se o intervalo de 95% da diferença de AUC ficar acima de zero.** Para não escolher o vencedor depois, também reportamos as três redes contra a Logística-16, cada uma com o próprio intervalo.
- **Controle de atalho:** reportar a AUC e o intervalo. Se ela ficar bem acima de 0,5, os ganhos da pose são lidos com cautela.

## O que fica fora

- Ajustar canais, atributos ou hiperparâmetros olhando as dobras de teste.
- Normalização por pessoa (ideia 2) e janelas mais longas (ideia 5), que ficam para outra etapa.
- A imagem do rosto direto na rede (ideia 6).
