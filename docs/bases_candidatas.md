# Bases candidatas (busca de 12/11/2026)

Resultado da frente A do plano pós-entrega intermediária. Cinco buscas em paralelo: Leste da Ásia; Sul e Sudeste da Ásia e Oriente Médio; Europa, incluindo Rússia; Américas, África e Oceania; e uma busca por tipo de base, a partir de artigos de revisão. Cada busca usou também termos nos idiomas locais.

**Como ler:** "conferido" quer dizer que a página da base ou o artigo foi aberto. "Parcial" quer dizer que só a busca ou um resumo confirmou. Dados marcados como "não informado" não apareciam na fonte. Nada foi baixado ainda, e os números de cada base vêm das páginas e artigos, não de inspeção nossa.

## Conclusão principal

**Fora do FL3D, do NITYMED e do DMD, não achamos nenhuma base pública com microssono espontâneo marcado no tempo.** Nenhuma das 5 buscas encontrou uma. Os trabalhos de vários países (incluindo Brasil, México, Chile, Irã e Malásia) usam NTHU-DDD, UTA-RLDD ou DROZY, ou gravam dados próprios que não publicam. O SHRP2 (EUA) tem microssono em direção real, mas o vídeo do rosto só pode ser usado num enclave físico na Virginia. Essa lacuna é da área, não do projeto, e entra no paper.

A parte de sonolência do **DMD** tem olho fechado, piscada e bocejo por frame, mas o guia da base (recebido em 13/11) diz que os estados foram **encenados**, com o carro parado e sem sono real. Como a **BINUS** já tem 93 fechamentos de 1 s ou mais em vídeo (ver abaixo), o DMD não foi baixado e fica só como citação.

## Por uso

### Microssono e olho fechado no tempo

| Base | País | O que tem | Acesso | Conferido |
| --- | --- | --- | --- | --- |
| **DMD** (parte de sonolência) | Espanha | Olho fechado, piscada e bocejo por frame, RGB na versão pública; **estados encenados**, carro parado | Formulário (acesso recebido em 13/11), CC BY-NC-ND 4.0 | Sim (guia da base). Descartada: encenada, e a BINUS cobre o papel |
| **FatigueView** (2022) | China | RGB e IR, 5 câmeras, piscada, bocejo e sonolência no tempo, 1.000+ h | Baidu Pan; licença dos dados incerta; parte das anotações após aprovação | Parcial. Um survey diz que a cena é simulada (cadeira de escritório) |
| **BINUS Raspberry Pi 5** (2025) | Indonésia | 32 pessoas, olho aberto/fechado e bocejo em imagens e vídeo, RGB com LED IR, óculos, boné e hijab | **Livre, CC BY 4.0** (Mendeley) | Sim |

### Sonolência com alerta e sonolento da mesma pessoa

| Base | País | O que tem | Acesso | Conferido |
| --- | --- | --- | --- | --- |
| **UL-DD** (2025) | EUA e Finlândia | 19 pessoas, sessão alerta e sonolenta de 40 min, KSS a cada 4 min, rosto em IR e profundidade a 60 fps | Zenodo restrito: e-mail institucional e acordo de uso; 14,7 TB no total (cerca de 35 GB de IR por pessoa) | Sim |
| **WACHsens** (2021–22) | Áustria (TU Graz) | Simulador, mesma pessoa descansada e cansada, 196 testes de 50 motoristas avaliados por especialista no tempo (alerta, moderado, extremo e dormindo/microssono). **Sem vídeo do rosto:** os dados são sinais em CSV, com abertura da pálpebra do SmartEye a 100 Hz, posição da cabeça, olhar, EEG e EOG | TRYOUT (3,5 GB) aberto, mas sob contrato de transferência só para pesquisa; FULL (880 GB) e SMALL por e-mail | Sim (documentação lida) |
| **UNC Drowsy Driving** (2018) | EUA | Cerca de 10 pessoas, simulador, KSS a cada 5 min (segundo o artigo) | Formulário | Sim (página) |
| **MFD** | China | 19 pessoas, 2 sessões de 2 h, RGB-D do rosto e EEG, fadiga pelo PERCLOS | IEEE DataPort, exige assinatura paga (conferido em 13/11 com conta logada) | Sim. **Descartada:** paga, e o rótulo pelo PERCLOS impede testar se uma rede supera o PERCLOS |
| **SUST-DDD** (2022) | Turquia | 19 pessoas, 2.074 clipes de 10 s, direção real com celular, rótulo de observador | **Baixada** pelo Kaggle (licença "Unknown") | Sim |
| **DriverMVT** (2022) | Rússia | 9 motoristas, sonolência e pose da cabeça, números inconsistentes no artigo | Link de download não achado | Parcial |

### Piscadas (falsos alarmes)

| Base | País | O que tem | Acesso | Conferido |
| --- | --- | --- | --- | --- |
| **Eyeblink8** (2014) | Eslováquia | 408 piscadas por frame, 640×480 | **Download direto**, GPL3 | Sim |
| **Researcher's Night** (2016) | Eslováquia | 107 vídeos, 1.849 piscadas, 15 e 30 fps | Por pedido, GPL3 | Sim |
| **MPEblink** (2023) | China e Singapura | 686 vídeos de filmes, 8.748 piscadas com início e fim | **Livre** (Zenodo e Hugging Face); licença dos dados não informada | Sim |
| **mEBAL2** (2023) | Espanha | 180 sessões, cerca de 10.500 piscadas, RGB e NIR | Acordo assinado | Sim |
| **RT-BENE** (2019) | Reino Unido | Mais de 200 mil recortes de olho em RGB, aberto ou piscando | **Livre**, 937 MB, CC BY-NC-SA 4.0 | Sim |

### Distração, olhar para baixo e pose da cabeça

| Base | País | O que tem | Acesso | Conferido |
| --- | --- | --- | --- | --- |
| **Drive&Act** (2019) | Alemanha | 12 h, NIR, profundidade e RGB, 83 atividades | **Livre** para pesquisa, sem login | Sim |
| **DGW** (2021) | Austrália e Índia | 338 pessoas, webcam RGB, 9 zonas de olhar | E-mail ao autor | Sim |
| **SynDD1 / AI City Track 3** | EUA | Distração, bocejo e zonas de olhar com início e fim; até 99 motoristas | Pedido ao autor / formulário | Sim |
| **100-Driver** (2023) | China e Itália | 100 motoristas, 22 classes, RGB e NIR | Formulário | Sim |
| **EBDD** (2018) | Bangladesh | 59 clipes de direção real, celular e outras distrações | Download livre, senha por e-mail | Sim |
| **AutoPOSE** (2020) | Alemanha | Pose da cabeça medida com captura de movimento, IR e Kinect | Download público | Sim |
| **DAD** (2021) | Alemanha | 31 pessoas, IR e profundidade, direção normal ou anômala | Licença, cerca de 95 GB | Sim |
| **3MDAD** (2020) | Tunísia e França | Kinect frontal, de dia RGB e à noite IR | CC BY-NC-ND (Kaggle ou e-mail) | Parcial |

### Sintéticas

| Base | País | O que tem | Acesso | Conferido |
| --- | --- | --- | --- | --- |
| **UnityEyes** (2016) | Reino Unido | Gerador de imagens da região do olho com pálpebra animada; falta saber se fecha totalmente | Download livre | Sim |
| **Gerador "Blinking Beyond EAR"** (2025) | Alemanha e Austrália | Avatar no Blender com piscadas sorteadas; propõe um ângulo da pálpebra mais estável que o EAR | Ainda não liberado | Sim (artigo) |
| VigiDriver | não informado | É o UTA-RLDD com brilho, reflexo e ruído sintéticos, não uma base nova | IEEE DataPort, assinatura | Parcial |
| FatigueFace-1156 (2026) | não informado | 1.156 imagens em 8 classes (olho fechado, bocejo, pose), todas geradas a partir de **uma única foto de uma pessoa** | IEEE DataPort, assinatura | Sim. Descartada: um rosto só |

## Só para citar no paper

- **SHRP2** (EUA): microssono e sonolência em direção real, mas o rosto só no enclave do VTTI.
- **AI Hub 졸음운전** (Coreia): olho aberto/fechado e direção do rosto em motoristas profissionais. Não confirmamos se estrangeiros podem baixar.
- **SEED-VIG/VLA/VRW** (China), **AdVitam** (Suíça) e **Cao et al. 2019** (Taiwan): sonolência com EEG ou fisiologia, sem vídeo do rosto.
- **HADRIAN** (Espanha), **ZUT Szczecin** (Polônia), **D3S** (Índia), **manD 1.0** (Alemanha), **PhysDrive** (China), **AIDE** (China): pouco úteis ou sem acesso confirmado.

## Baixadas em 12/11/2026

Todas em `data/bases_novas/` (fora do Git), cada uma na sua pasta. Os zips foram conferidos (abrem e têm o tamanho anunciado).

| Base | Arquivos | Tamanho | Uso previsto |
| --- | --- | --- | --- |
| Eyeblink8 | `eyeblink8/eyeblink8.zip` (8 vídeos com anotação de piscada) | 313 MB | Quantas piscadas a regra de 1 s transforma em alarme (a seção 6.2 só estimou isso) |
| RT-BENE | `rt_bene/`: só as 4 pessoas da dobra de validação dos autores (s000, s011, s015, s016), com etiquetas e `rt_bene_subjects.csv` | 266 MB | Teste do classificador de olho em RGB (frente J). A s006 foi descartada pelos autores |
| BINUS Raspberry Pi 5 | `binus_rpi5/binus_rpi5.zip` (`modelling` em imagens e `other_testing` em vídeo) | 1,22 GB | Microssono fora do FL3D: nos 47 vídeos de teste (46,8 min, anotação a cada 5 frames, ou 6 por segundo), há 93 fechamentos de 1 s ou mais, 25 deles durante bocejo, e 3 de 3 s ou mais (o maior com 3,2 s). Também testa o filtro de bocejo. Os vídeos não identificam a pessoa, o que não importa para teste |
| SUST-DDD | `SUST-DDD/SUST Driver Drowsiness Dataset/` (`drowsiness/d_N.mp4` e `not drowsiness/n_N.mp4`; o zip foi apagado depois de conferido) | 4,77 GB | Sonolência em direção real, treino e teste por motorista. Vídeo vertical 720×1280 a 25 ou 30 fps. Um arquivo tem o nome errado (`n_790mp4.mp4`). Checagem de continuidade em `data/cache/sust/continuidade.csv`: cerca de 70% das junções entre clipes de número seguido são contínuas, o que dá 87 sequências de 1 min ou mais (42 sonolentas e 45 não sonolentas, até 10 min). Conferido a olho em 6 junções: as contínuas são o mesmo vídeo, e as quebras podem ser outro vídeo da mesma pessoa ou outra pessoa. **Motoristas agrupados à mão em 13/11** (folhas de contato com um quadro por sequência, conferidas pelo Rafael): 20 grupos em `data/cache/sust/motoristas.csv` (o README fala em 19). Os clipes seguem a ordem dos motoristas nas duas classes, e a mesma pessoa aparece com a mesma roupa nos dois estados. Um motorista (P21) só tem clipes sonolentos, e P20 e P22 têm 11 e 6 não sonolentos. Com isso, a base serve para **treinar e testar** com validação cruzada por motorista |
| Drive&Act | `driveandact/a_column_driver.zip` (câmera NIR da coluna A do motorista) e `iccv_activities_3s.zip` (anotações) | 2,68 GB | Regra de olhar para baixo (frente E) |
| WACHsens | `wachsens/Documentation.zip` (11 PDFs) e o contrato de transferência não comercial | 52 MB | Decidir se vale baixar o TRYOUT |

**Não baixadas:**
- **MPEblink:** 21,6 GB, não cabe no disco.
- **AutoPOSE:** exige login e tem cerca de 100 GB.
- **DMD:** o portal só funciona no navegador.

Estas três ficam para o Colab, se forem usadas.

## Sugestão de uso até 17/11

**Já baixadas:** ver a tabela acima. Nenhuma é usada para treinar ou escolher limiar sem protocolo escrito antes.

**Em andamento (13/11):**
- **WACHsens TRYOUT:** contrato aceito. O download direto falha porque o servidor corta a conexão (o melhor chegou a 427 MB de 3,5 GB) e não aceita retomar. Vai ser baixado pelo Colab.
- **UL-DD:** acesso pedido no Zenodo em 13/11, com o e-mail do Insper. O acesso é pessoal: os dados não podem ser compartilhados nem levados ao Colab.
- **DMD:** descartado (estados encenados; a BINUS cobre o microssono).

**Pedir acesso já (a resposta pode não chegar a tempo):** UL-DD, WACHsens FULL ou SMALL, DGW, SynDD1, UNC e mEBAL2. Os pedidos precisam sair do e-mail institucional do grupo.

**Teste novo do MIL-Transformer:** só é possível com UL-DD, WACHsens ou UNC. Se nenhuma chegar até 15/11, fica como trabalho futuro.
