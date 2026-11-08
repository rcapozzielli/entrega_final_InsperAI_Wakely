# Wakely

Protótipo acadêmico de detecção de sonolência ao volante com câmera e deep learning, desenvolvido por um grupo de 3 trainees da Insper AI como entrega final.

**O Wakely não é um dispositivo de segurança e nunca deve ser testado dirigindo.**

## Status

A pesquisa está concluída, e o notebook ([`wakely.ipynb`](wakely.ipynb)) já roda a linha de base, a CNN de olho, o filtro de bocejo, o agente de RL, o modelo temporal (GRU, TCN e transformer), a análise de erros dos modelos de sonolência e uma rede MIL com validação externa no DROZY. A demo com webcam ainda falta.

| Etapa | Estado | Resultado no teste |
| --- | --- | --- |
| Linha de base: MediaPipe + EAR + regras do Euro NCAP | Feita | Microssono por frame: F1 0,66; com T = 1 s, alerta em 7 de 26 episódios e 3 falsos alarmes |
| CNN de olho (MobileNetV3-Small, MRL Eye separado por pessoa) | Feita | 97,0% de acurácia em 8 pessoas novas |
| CNN no vídeo, no lugar do EAR | Feita | Microssono por frame: F1 0,75; com T = 1 s, alerta em 13 de 26 episódios e 6 falsos alarmes |
| Comparação com a YOLO26n classificadora (5 sementes) | Feita | Acurácia de 97,7% contra 96,8% da MobileNetV3; 84,5% contra 73,5% dos episódios de 1 s ou mais nos 44 vídeos |
| Filtro de bocejo e teste de piscadas | Feita | YOLO com filtro: 86,8% dos episódios de 1 s ou mais e 10 falsos alarmes nos 44 vídeos, contra 84,5% e 33 sem filtro |
| Agente de RL no alerta (Q-learning, piso de 3 s) | Feito | Não supera a regra: com YOLO e λ = 10, 90% dos episódios de 1 s ou mais e 13 falsos alarmes (2 fortes), contra 90% e 10 da regra com piso. Os números do YOLO mudam com a GPU |
| Falsos alarmes em pessoas acordadas (UTA-RLDD) | Feito | 6,7 alarmes por hora em 9,5 h; 90% das pessoas sem nenhum, e uma pessoa com 40 dos 64 |
| Modelo temporal (GRU e TCN, UTA-RLDD) | Feito | Não supera o PERCLOS: AUC 0,750 (GRU) e 0,754 (TCN), contra 0,774 do PERCLOS do minuto |
| Modelo temporal com cabeça, expressões e transformer (protocolo fixado antes) | Feito | Nenhuma rede supera a logística com os mesmos sinais (AUC 0,772): transformer 0,754, TCN 0,736 e GRU 0,729 |
| Análise de erros dos modelos de sonolência | Feita | AUC de cerca de 0,85 dentro da pessoa e 0,77 entre pessoas; os 9 modelos erram os mesmos vídeos |
| Rede MIL normalizada pelo 1º minuto, com validação externa no DROZY (protocolo fixado antes) | Feita | Supera a logística com os mesmos sinais no UTA (AUC 0,742 contra 0,654) e no DROZY (0,708 contra 0,575), mas não o PERCLOS absoluto no UTA (0,814) |
| Demo com webcam | A fazer | |

T é o tempo de olho fechado até o alerta. Usamos T = 1 s, o limite inferior da faixa de microssono do Euro NCAP. Dos 26 episódios do teste, só 14 duram 1 s ou mais: neles, o EAR acha 7 e a CNN, 13. Na calibração, os dois quase empatam (114 e 111 de 228 episódios), e o resultado da CNN varia entre treinos.

Usando os 44 vídeos, com o limiar de cada vídeo escolhido nos outros, o EAR com filtro de mediana acha 79% dos episódios de 1 s ou mais (130 de 165) com 30 falsos alarmes, e a CNN, 66% (109 de 165) com 56. Os intervalos de confiança se sobrepõem, então a CNN ainda não superou o EAR.

Com 5 sementes, a YOLO26n-cls supera a MobileNetV3 nos 44 vídeos (11 pontos a mais, intervalo de +3,7 a +19,4), mas nenhuma das duas supera o EAR de forma conclusiva. A biblioteca `ultralytics` é AGPL-3.0, e por isso o repositório é público, com a mesma licença.

Quase todos os falsos alarmes estavam ligados a bocejos, então o sistema passou a ignorar o olho fechado durante um bocejo detectado pela abertura da boca. Isso reduz o total em cerca de 23 alarmes nos três sinais. A base não mostra microssono junto de bocejo, que é o maior risco dessa escolha. Recolocando os frames que o FL3D removeu, T = 1 s parece segurar as piscadas (cerca de 1% dos buracos curtos atravessados por um alarme), mas sobram alarmes em trechos sem rótulo, então a taxa real de falso alarme ainda não está medida.

A seção 7 testa um agente de reinforcement learning que decide, durante o olho fechado, entre esperar, aviso leve e aviso forte, com uma tecla de "foi alarme falso" simulada. Ele aprende sozinho a ignorar o bocejo e a avisar mais cedo quando a pessoa já teve vários fechamentos longos, mas não supera a regra com estes dados. Ela também testa um piso de 3 s que dispara mesmo durante bocejo: com o YOLO, ele custa 2 alarmes nos 44 vídeos.

A seção 8 usa o UTA-RLDD recortado: 1.126 clipes de 1 minuto, de 60 pessoas, alertas ou sonolentas, com rótulo autorrelatado. Em 9,5 horas de pessoas acordadas, a regra da demo dá 6,7 falsos alarmes por hora, mas 90% das pessoas não têm nenhum, e uma pessoa sozinha dá 40 dos 64. Os alarmes se concentram em quem tem o olho aberto menor na imagem. Para estimar a sonolência no minuto, com 5 dobras por pessoa, o PERCLOS sozinho chega a AUC de 0,77. A regressão logística sobre 6 atributos, a GRU e a TCN treinadas do zero ficam entre 0,75 e 0,76, sem diferença conclusiva: com estes sinais, o padrão de 1 minuto já está resumido no PERCLOS.

A seção 8.5 deu às redes o movimento da cabeça e as expressões do rosto (blendshapes do MediaPipe) e testou também um transformer, com o protocolo fixado antes do treino ([`docs/protocolo_8_5.md`](docs/protocolo_8_5.md)). A logística com os sinais novos chega a 0,772, e nenhuma rede a supera: a GRU e a TCN ficam piores de forma conclusiva, e o transformer empata. A análise de erros (seção 8.6) mostra que os modelos ordenam bem os minutos dentro de cada pessoa, mas três problemas da base limitam todos eles:
- o tamanho do olho na imagem varia entre pessoas tanto quanto o efeito do sono;
- o rótulo vale para o vídeo inteiro e erra nos primeiros minutos dos vídeos sonolentos;
- cada classe foi gravada num dia diferente, então a base não permite separar o sono da sessão de gravação.

A seção 8.7 ataca esses problemas, com outro protocolo fixado antes ([`docs/protocolo_8_7.md`](docs/protocolo_8_7.md)). Cada vídeo é normalizado pelo seu 1º minuto, e uma rede MIL (*multiple instance learning*) trata o vídeo como um saco de minutos com um único rótulo, com atenção sobre os minutos. A rede principal (GRU) supera de forma conclusiva a logística com os mesmos sinais normalizados no UTA (+0,089, de +0,007 a +0,181). A vantagem se repete no DROZY (Massoz et al., WACV 2016), com 14 pessoas novas, câmera infravermelha e privação de sono controlada, usando a rede treinada só no UTA (+0,133). Pelo critério fixado antes, o deep learning se justifica na etapa de sonolência, com três limites:
- no UTA, o PERCLOS absoluto ainda é melhor que a rede;
- a atenção não acrescenta nada à média simples dos minutos;
- o DROZY é pequeno.

O transformer como codificador de minuto foi o melhor modelo nas duas bases (0,875 e 0,743), mas era secundário no protocolo.

O teste em vídeo é pequeno (2 vídeos com microssono), e 2 dos seus 5 motoristas também aparecem no treino dos autores do FL3D. As escolhas abaixo continuam sendo a proposta atual, a validar com o grupo e nos testes.

## Proposta de pipeline

![Pipeline recomendado](docs/pipeline_recomendado.png)

1. Uma webcam capta o rosto do motorista.
2. O MediaPipe localiza os olhos.
3. Um classificador com fine-tuning estima se o olho está fechado em cada frame. Vamos comparar MobileNetV3 e YOLO26n classificadora.
4. Uma medida dos últimos minutos estima o nível de sonolência. A demo mostra lado a lado o PERCLOS do último minuto, o mais simples, e a rede MIL da seção 8.7, com calibração no 1º minuto de uso, que se transferiu melhor para uma base nova. As duas estão prontas em [`demo/sonolencia.py`](demo/sonolencia.py).
5. Uma regra simples dispara o alerta quando o olho fica fechado por tempo prolongado.

## Conteúdo

| Arquivo | O que é |
| --- | --- |
| [`wakely.ipynb`](wakely.ipynb) | Notebook: dados, linha de base EAR, CNN de olho, avaliação em vídeo, agente de RL no alerta e modelo temporal |
| [`demo/sonolencia.py`](demo/sonolencia.py) | Extração por quadro, PERCLOS do último minuto e rede MIL ao vivo, para a demo. Usa `data/modelos/mil_gru4_uta.pt`, gravado pela seção 8.7 |
| [`pyproject.toml`](pyproject.toml) e `uv.lock` | Ambiente (Python 3.12, PyTorch com CUDA, MediaPipe, Ultralytics) |
| [`docs/pesquisa_wakely.md`](docs/pesquisa_wakely.md) | Pesquisa sobre biologia, indústria, arquitetura, datasets, avaliação e ética |
| [`docs/pipeline_recomendado.png`](docs/pipeline_recomendado.png) | Diagrama do pipeline |
| [`entrega_final.pdf`](entrega_final.pdf) | Enunciado da entrega |

Para começar, leia o resumo e as decisões do grupo na pesquisa.

## Como rodar

```bash
uv sync
uv run jupyter nbconvert --to notebook --execute --inplace wakely.ipynb
```

Também dá para abrir o `wakely.ipynb` no VS Code com o kernel do `.venv`. A seção 1 do notebook baixa o MRL Eye (342 MB), o FL3D (645 MB, do Kaggle, sem login) e o modelo do MediaPipe para `data/`, a seção 6 baixa o NITYMED (697 MB, do Kaggle) a seção 8, a pasta `len60` do UTA-RLDD recortado (1,2 GB, do Kaggle), e a seção 8.7, o DROZY (2,5 GB, do repositório ORBi da Universidade de Liège; a licença permite só pesquisa e proíbe mostrar as imagens). A primeira execução leva cerca de 30 minutos, quase tudo no MediaPipe, mais cerca de 2,5 horas na CPU para extrair os sinais do UTA-RLDD. Depois disso, landmarks e pesos ficam em cache em `data/`.

## Prazos

- 12/11/2026: apresentação intermediária
- 17/11/2026: entrega final (notebook e paper)
- 18/11/2026: apresentação final

## Dados

Não versione datasets, vídeos ou pesos de modelos neste repositório. Eles são grandes, e os dados contêm rostos de pessoas. Consulte as licenças de cada base na seção de datasets da pesquisa.
