#!/usr/bin/env python3
"""Emit n8n Workflow SDK TypeScript for the Muvstok receiver workflow."""
from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
WF = json.loads((REPO_ROOT / "n8n/workflows/cdp_stokapi.json").read_text(encoding="utf-8"))

NODE_BY_NAME = {n["name"]: n for n in WF["nodes"]}


def js(name: str) -> str:
    return NODE_BY_NAME[name]["parameters"]["jsCode"]


def sheets_append(name: str) -> str:
    p = NODE_BY_NAME[name]["parameters"]
    return json.dumps(
        {
            "resource": "sheet",
            "operation": "append",
            "documentId": p["documentId"],
            "sheetName": p["sheetName"],
            "columns": p["columns"],
            "options": p.get("options", {}),
        },
        ensure_ascii=False,
    )


def sheets_update(name: str) -> str:
    p = NODE_BY_NAME[name]["parameters"]
    return json.dumps(
        {
            "resource": "sheet",
            "operation": "update",
            "documentId": p["documentId"],
            "sheetName": p["sheetName"],
            "columns": p["columns"],
            "options": p.get("options", {}),
        },
        ensure_ascii=False,
    )


def if_params(name: str) -> str:
    return json.dumps(NODE_BY_NAME[name]["parameters"], ensure_ascii=False)


def main() -> None:
    extract_js = js("📊 Extrair linhas API Diversos")
    historico_js = js("📊 Construir Historico API Diversos")
    sku_js = js("📋 SKUs para atualizar")
    tg_js = js("📣 Formatar Telegram")
    invalid_js = js("🚫 Secret inválido")

    out = f'''import {{ workflow, node, trigger, ifElse, expr }} from '@n8n/workflow-sdk';

const webhook = trigger({{
  type: 'n8n-nodes-base.webhook',
  version: 2,
  config: {{
    name: '🔔 Webhook API Diversos Result',
    parameters: {{
      httpMethod: 'POST',
      path: 'muvstok-result',
      options: {{ rawBody: true }},
    }},
  }},
}});

const verifySecret = ifElse({{
  version: 2,
  config: {{
    name: '🔐 Verificar Webhook Secret',
    parameters: {if_params("🔐 Verificar Webhook Secret")},
  }},
}});

const extract = node({{
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {{
    name: '📊 Extrair linhas API Diversos',
    parameters: {{
      mode: 'runOnceForAllItems',
      jsCode: {json.dumps(extract_js, ensure_ascii=False)},
    }},
  }},
}});

const saveDetalhado = node({{
  type: 'n8n-nodes-base.googleSheets',
  version: 4.5,
  config: {{
    name: '📊 Salvar → CDP_Resultados (Detalhado)',
    parameters: {sheets_append("📊 Salvar → CDP_Resultados (Detalhado)")},
    retryOnFail: true,
    maxTries: 5,
    waitBetweenTries: 2000,
  }},
}});

const historicoBuild = node({{
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {{
    name: '📊 Construir Historico API Diversos',
    executeOnce: true,
    parameters: {{
      mode: 'runOnceForAllItems',
      jsCode: {json.dumps(historico_js, ensure_ascii=False)},
    }},
  }},
}});

const saveHistorico = node({{
  type: 'n8n-nodes-base.googleSheets',
  version: 4.5,
  config: {{
    name: '📊 Salvar → CDP_Resultados (Historico)',
    parameters: {sheets_append("📊 Salvar → CDP_Resultados (Historico)")},
    retryOnFail: true,
    maxTries: 5,
    waitBetweenTries: 2000,
  }},
}});

const skuForUpdate = node({{
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {{
    name: '📋 SKUs para atualizar',
    executeOnce: true,
    parameters: {{
      mode: 'runOnceForAllItems',
      jsCode: {json.dumps(sku_js, ensure_ascii=False)},
    }},
  }},
}});

const updateSkus = node({{
  type: 'n8n-nodes-base.googleSheets',
  version: 4.5,
  config: {{
    name: '✅ Atualizar CDP_SKUs',
    parameters: {sheets_update("✅ Atualizar CDP_SKUs")},
  }},
}});

const formatTelegram = node({{
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {{
    name: '📣 Formatar Telegram',
    executeOnce: true,
    parameters: {{
      mode: 'runOnceForAllItems',
      jsCode: {json.dumps(tg_js, ensure_ascii=False)},
    }},
  }},
}});

const sendTgCheck = ifElse({{
  version: 2,
  config: {{
    name: 'Enviar Telegram?',
    parameters: {if_params("Enviar Telegram?")},
  }},
}});

const telegram = node({{
  type: 'n8n-nodes-base.telegram',
  version: 1.2,
  config: {{
    name: '📱 Telegram',
    parameters: {{
      chatId: expr('{{ $json.telegram_chat_id }}'),
      text: expr('{{ $json.telegram_text }}'),
      additionalFields: {{ parse_mode: 'Markdown' }},
    }},
  }},
}});

const invalidSecret = node({{
  type: 'n8n-nodes-base.code',
  version: 2,
  config: {{
    name: '🚫 Secret inválido',
    parameters: {{
      mode: 'runOnceForAllItems',
      jsCode: {json.dumps(invalid_js, ensure_ascii=False)},
    }},
  }},
}});

export default workflow('t160mzGPYYlJcrjZ', 'cdp_muvstok-api_receiver')
  .add(webhook)
  .to(
    verifySecret
      .onTrue(extract.to(saveDetalhado))
      .onTrue(extract.to(historicoBuild.to(saveHistorico)))
      .onTrue(
        extract
          .to(skuForUpdate.to(updateSkus))
          .to(formatTelegram.to(sendTgCheck.onTrue(telegram)))
      )
      .onFalse(invalidSecret)
  );
'''
    path = REPO_ROOT / "n8n/sdk/muvstok_receiver.workflow.ts"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(out, encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
