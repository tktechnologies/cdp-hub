# Reunião — Nova arquitetura CDP: um comando, duas consultas

**Sugestão de título:** *CDP: `.analisar` agora busca sites e estoque Muvstok juntos*  
**Duração:** 20–25 minutos (+ 5 min perguntas)  
**Público:** usuários do Telegram/e-mail, operação, gestão  
**Material visual:** [CDP_DUAL_ANALISE_ARCHITECTURE.md](../CDP_DUAL_ANALISE_ARCHITECTURE.md) (diagramas Mermaid)

---

## Objetivo da reunião

Explicar, em linguagem simples, que **não é preciso disparar duas rotinas**: um `.analisar` já faz a consulta nos **sites de peças** e no **Muvstok**, e cada parte avisa quando termina.

**Mensagem principal:** *“Um clique, duas respostas — sempre 5 peças por vez.”*

---

## Agenda sugerida

| Min | Tópico | O que mostrar |
|-----|--------|----------------|
| 0–3 | Contexto | Por que unificamos (menos passo manual, mesma fila de SKUs) |
| 3–8 | Antes × Agora | Diagrama 1 no doc de arquitetura |
| 8–12 | O que o usuário faz | Demo ou print: `.analisar` no Telegram |
| 12–17 | O que o usuário recebe | Mensagem de início + 2 avisos de conclusão |
| 17–20 | Planilhas | `cdp_skus` (fila) e `cdp_resultados` (resultados) |
| 20–25 | Perguntas | FAQ abaixo |

---

## Roteiro para apresentador (fala sugerida)

### 1. Abertura (30 s)

> “Hoje o CDP responde duas perguntas que vocês já faziam separado: **‘quanto custa nos sites?’** e **‘o que temos no Muvstok?’**. Agora isso sai do **mesmo comando** que vocês já conhecem: `.analisar`.”

### 2. Antes × Agora (2 min)

**Antes**

- `.analisar` → só sites → 1 mensagem no final  
- Muvstok → outro processo / manual  

**Agora**

- `.analisar` → sites **e** Muvstok ao mesmo tempo → **2 mensagens** no final (uma de cada)

*Mostrar Diagrama 1 — “Visão do usuário”.*

### 3. Passo a passo na prática (3 min)

1. Você manda `.analisar` (Telegram ou e-mail autorizado).  
2. O sistema confirma: *“Iniciamos Scraper + Muvstok”* e quantas peças (5).  
3. Em segundo plano rodam **duas filas** em paralelo — não precisa esperar uma para começar a outra.  
4. Quando os **sites** terminam → **primeiro aviso** (resumo / planilha).  
5. Quando o **Muvstok** termina → **segundo aviso** (estoque / detalhe).

*Mostrar Diagrama 2 — sequência.*

### 4. Por que 5 peças? (1 min)

> “Continuamos em modo de **amostra controlada**: 5 SKUs por rodada para não sobrecarregar sites, API e planilha. Isso já era assim na busca em sites; agora o Muvstok usa **a mesma amostra**.”

### 5. Onde ver os resultados (2 min)

| O quê | Onde |
|--------|------|
| Fila de peças a processar | Planilha **cdp_skus** — coluna PROCESSADO |
| Preços nos sites | **cdp_resultados** — abas Detalhado / Resumo |
| Estoque Muvstok | **cdp_resultados** — detalhe Muvstok (receiver) |
| Avisos rápidos | Telegram ou e-mail (quem pediu) |

### 6. O que **não** mudou (1 min)

- Comandos `.sku` (lista pontual) → **sites + StokAPI**, mesma lógica dual do `.analisar` (até 5 SKUs).  
- Segurança: só chats/e-mails autorizados.  
- Planilha mestra de SKUs — mesma.

### 7. Demo ao vivo (opcional, 3 min)

1. Telegram: enviar `.analisar`.  
2. Mostrar mensagem de início (Scraper + Muvstok).  
3. Abrir n8n ou planilha se a audiência for técnica; senão aguardar os 2 avisos.

---

## Slide único — “cola” visual (ASCII)

Copiar para slide ou Notion:

```
┌─────────────────────────────────────────────────────────┐
│  VOCÊ:  .analisar  (Telegram ou e-mail)                 │
└───────────────────────────┬─────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
     ┌─────────────────┐         ┌─────────────────┐
     │  SITES DE PEÇAS │         │    MUVSTOK      │
     │  GM, ML, VW…    │         │    estoque      │
     └────────┬────────┘         └────────┬────────┘
              │                           │
              ▼                           ▼
     ┌─────────────────┐         ┌─────────────────┐
     │  Aviso 1        │         │  Aviso 2        │
     │  "Sites prontos"│         │  "Muvstok OK"   │
     └─────────────────┘         └─────────────────┘

        Planilha cdp_skus  →  fila (5 peças/rodada)
        Planilha resultados →  tudo gravado
```

---

## FAQ (linguagem normal)

**Preciso mandar dois comandos?**  
Não. Só `.analisar`.

**Vou receber quantas mensagens?**  
Uma de “começou” e depois **até duas** de “terminou” (sites e Muvstok).

**Posso pedir mais de 5 peças?**  
Nesta fase, não — fixo em 5 por rodada para estabilidade.

**E se o Muvstok falhar e os sites ok?**  
Você ainda recebe o aviso dos sites; a equipe técnica vê o erro no Muvstok nos logs/n8n.

**O `.sku` com lista minha muda?**  
Não dispara Muvstok — só busca em sites (comportamento anterior).

**Quem recebe o Telegram?**  
Quem enviou `.analisar` (chat autorizado), não um número fixo interno.

---

## Checklist pós-reunião

- [ ] Confirmar lista de chats/e-mails autorizados (`TELEGRAM_ALLOWED_CHAT_IDS`, `EMAIL_ALLOWED_SENDERS`)
- [ ] Fazer um `.analisar` de teste em produção e validar 2 avisos
- [ ] Registrar data da reunião e participantes abaixo

### Participantes / data

| Campo | Preencher |
|-------|-----------|
| Data | |
| Participantes | |
| Decisões | |
| Ações | |

---

## Anexo técnico (se perguntarem)

- Diagramas completos: [CDP_DUAL_ANALISE_ARCHITECTURE.md](../CDP_DUAL_ANALISE_ARCHITECTURE.md)  
- Deploy 2026-05-22: [dual_analisar_muvstok_20260522.md](../validation/dual_analisar_muvstok_20260522.md)  
