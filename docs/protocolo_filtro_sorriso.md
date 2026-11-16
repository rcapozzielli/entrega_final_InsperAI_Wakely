# Protocolo: filtro de sorriso no alerta de microssono

Escrito em 15/11/2026, **antes de calcular qualquer número com os blendshapes de sorriso** em qualquer base, e aprovado pelo Rafael no mesmo dia (ver o critério). Segue a seção 10.4 e as definições de `docs/protocolo_metricas_f.md` e `docs/protocolo_testes_bases_novas.md`.

## De onde vem a ideia

Usando a demo, o Rafael viu que o sistema dá alarme de microssono quando ele sorri. A explicação provável: no sorriso as bochechas sobem e apertam os olhos, e o olho apertado parece fechado para o YOLO e para o EAR. Microssono durante um sorriso é muito improvável.

Como a ideia veio do rosto de uma pessoa só, ela é uma **hipótese**. Pela seção 10.3, as gravações do grupo servem para propor filtros, e nunca para confirmar. A confirmação vem de bases com outras pessoas.

## O filtro (fixado aqui, não muda olhando os resultados)

- **Sinal de sorriso:** média dos blendshapes `mouthSmileLeft` e `mouthSmileRight` do MediaPipe (0 a 1), que já fazem parte dos 61 sinais do `ExtratorRosto` (seção 8.5 e demo).
- **Sorriso ativo:** o sinal fica em 0,5 ou mais por 0,12 s seguidos, e o sorriso continua valendo por 1 s depois de cair. A persistência e a margem são as do filtro de bocejo (seção 6.1), convertidas pelo tempo. O limiar de 0,5 (metade da escala) é fixado aqui, sem olhar nenhuma base.
- **Efeito:** olho fechado durante sorriso ativo não conta para o aviso de microssono (T = 1 s), como no filtro de bocejo. Ele usa só quadros passados, para valer ao vivo.
- **O piso de 3 s continua valendo** (seção 6.4): olho fechado por 3 s ou mais avisa mesmo durante sorriso ou bocejo.
- **Sistema de base:** a fusão pela média, que é o sistema final de microssono (seção 11), com limiar 0,35, filtro de bocejo, T = 1 s e piso de 3 s. O limiar de olho **não** é reescolhido com o filtro.

## Bases e o que cada uma mede

| Base | Papel | O que se mede |
|---|---|---|
| FL3D, 44 vídeos | **Segurança:** o filtro não pode apagar microssonos | Acertos de 1 s ou mais, falsos alarmes e F2, com e sem o filtro, na validação cruzada (5 sementes do YOLO), com o mesmo limiar. O sorriso vem do `fl3d.npz` do Antônio (61 sinais por quadro), juntado por vídeo e frame |
| BINUS, 47 vídeos | **Segurança,** fora do FL3D | Acertos nos 152 fechamentos de 1 s ou mais, com e sem o filtro |
| UTA-RLDD, classe alerta (60 pessoas, 9,5 h) | **Ganho:** menos alarmes falsos em pessoas acordadas | Alarmes por hora, com e sem o filtro (todo alarme é falso) |
| Eyeblink8 (8 vídeos, 0,66 h) | **Ganho** | Idem |

Nas bases de acordados, a taxa é somada pesando pelo tempo, como na condição 2 da 10.4. Incerteza por bootstrap pareado por vídeo (por pessoa no UTA), 5.000 sorteios, IC95% pelos percentis.

## Critério (fixado antes)

O filtro entra no sistema final se as duas condições valerem:

1. **Segurança:** perde no máximo 1 acerto de 1 s ou mais no FL3D (média das 5 sementes) e no máximo 1 na BINUS.
2. **Ganho:** a taxa somada de alarmes por hora em acordados (UTA alerta + Eyeblink8) fica menor que sem o filtro. A comparação é de valores, como na condição 2 da 10.4. O IC95% da diferença (com filtro − sem filtro) é reportado, mas não é exigido.

A condição 1 não pergunta se alguém tem microssono sorrindo, o que é improvável. Ela mede se o MediaPipe **confunde** o rosto no microssono (cabeça caindo, boca relaxada) com um sorriso, o que silenciaria o alarme no pior momento. Com essa garantia, basta o filtro tirar algum alarme falso para valer a pena. Se a redução não tiver IC todo abaixo de zero, o paper a descreve como não conclusiva.

**Aprovado pelo Rafael em 15/11/2026,** com a condição 2 sem exigir intervalo, antes de calcular qualquer número com o sinal de sorriso.

Se passar, o filtro entra na demo (`demo/alerta.py`) e na seção 11. Se não passar, fica como resultado negativo, e a demo não muda.

## Descrição (não é critério)

- A fração dos alarmes falsos da fusão no UTA alerta e no Eyeblink8 que acontece com sorriso ativo.
- A distribuição do sinal de sorriso nos frames de microssono do FL3D, para mostrar o risco.
- Os resultados com os limiares 0,3 e 0,7 só como sensibilidade, sem trocar o 0,5.

## Riscos

- **Pouco sorriso nas bases de acordados:** o UTA é gente gravando a si mesma parada, então pode haver poucos sorrisos, e o ganho pode sair pequeno mesmo que o filtro funcione numa viagem com conversa.
- **Blendshape errando:** cabeça caindo ou boca relaxada no sono podem ligar o `mouthSmile`. É isso que a condição 1 mede.
- **O FL3D e a BINUS têm microssono encenado.**
- **A ideia veio do Rafael,** então as gravações dele não entram em nenhuma conclusão.
