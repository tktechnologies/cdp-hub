/**
 * CDP cdp_resultados audit — run once from Extensions > Apps Script.
 * Migrates Detalhado v2, refreshes Painel KPIs, extends Historico/Resumo headers.
 */
function applyCdpSheetsAudit() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  migrateDetalhado_(ss.getSheetByName('Detalhado'));
  refreshPainel_(ss.getSheetByName('Painel'));
  ensureHeaders_(ss.getSheetByName('Historico'), ['skus_not_found', 'skus_blocked', 'skus_error']);
  ensureHeaders_(ss.getSheetByName('Resumo'), ['STATUS_RESULTADO'], 'STATUS');
  SpreadsheetApp.flush();
}

function migrateDetalhado_(sh) {
  if (!sh) throw new Error('Detalhado tab missing');
  const CANONICAL = [
    'job_id', 'sku_pesquisado', 'sku_encontrado', 'correspondencia_exata', 'site', 'codigo_site',
    'status_resultado', 'has_valid_price', 'source_health', 'preco', 'preco-medio', 'moeda', 'condicao',
    'vendedor', 'uf', 'empresa', 'cnpj', 'url_produto', 'titulo_bruto', 'marca', 'regiao',
    'coletado_em', 'tempo_busca_ms', 'fonte_pipeline',
  ];
  const lastRow = sh.getLastRow();
  const lastCol = sh.getLastColumn();
  if (lastRow < 1) {
    sh.getRange(1, 1, 1, CANONICAL.length).setValues([CANONICAL]);
    return;
  }
  const headers = sh.getRange(1, 1, 1, lastCol).getValues()[0].map(String);
  const idx = {};
  headers.forEach((h, i) => {
    if (!h) return;
    if (h === 'origem') idx.regiao = i;
    else if (h === 'estado') idx.uf = i;
    else if (h === 'id_job') idx.job_id = i;
    else idx[h] = i;
  });
  const out = [CANONICAL];
  for (let r = 2; r <= lastRow; r++) {
    const row = sh.getRange(r, 1, r, lastCol).getValues()[0];
    const get = (name) => {
      const i = idx[name];
      return i === undefined ? '' : String(row[i] == null ? '' : row[i]);
    };
    const codigoSite = get('codigo_site').toLowerCase();
    const vendedor = get('vendedor');
    let empresa = get('empresa');
    if (!empresa || empresa === 'N/A' || empresa === vendedor) empresa = '';
    let titulo = get('titulo_bruto');
    const status = get('status_resultado').toUpperCase();
    if (/^(NOT_FOUND|BLOQUEADO:|TIMEOUT:|ERRO:|SEM_PRECO:)/i.test(titulo) ||
        ['NOT_FOUND', 'BLOCKED', 'TIMEOUT', 'ERROR', 'NOT_QUERIED'].indexOf(status) >= 0) {
      titulo = '';
    }
    const fonte = (codigoSite === 'api-diversos' || codigoSite === 'muvstok') ? 'API Diversos' : 'WEBSCRAPER';
    out.push([
      get('job_id'), get('sku_pesquisado'), get('sku_encontrado'), get('correspondencia_exata'), get('site'),
      codigoSite, status, get('has_valid_price'), get('source_health'), get('preco'), get('preco-medio'),
      get('moeda'), get('condicao'), vendedor, get('uf'), empresa, get('cnpj'), get('url_produto'), titulo,
      get('marca'), get('regiao') || get('origem'), get('coletado_em'), get('tempo_busca_ms'), fonte,
    ]);
  }
  sh.clear();
  sh.getRange(1, 1, out.length, CANONICAL.length).setValues(out);
}

function refreshPainel_(sh) {
  if (!sh) return;
  const hasPrice = 'REGEXMATCH(TO_TEXT(Detalhado!H2:H),"(?i)^(true|1|sim)$")';
  const skuOk = 'Detalhado!B2:B<>"",Detalhado!B2:B<>"SEM_DADOS"';
  const foundValid = 'Detalhado!G2:G="FOUND_PRICE",' + hasPrice;
  const parsedPrice = 'IF(REGEXMATCH(TO_TEXT(Detalhado!J2:J),","),VALUE(SUBSTITUTE(SUBSTITUTE(TO_TEXT(Detalhado!J2:J),".",""),",",".")),VALUE(Detalhado!J2:J))';
  const siteTable = '=LET(sites,SORT(UNIQUE(FILTER(Detalhado!E2:E,Detalhado!E2:E<>""))),hasPrice,' + hasPrice + ',parsedPrice,' + parsedPrice + ',found,MAP(sites,LAMBDA(s,COUNTUNIQUE(FILTER(Detalhado!B2:B,Detalhado!E2:E=s,' + foundValid + ')))),total,MAP(sites,LAMBDA(s,COUNTUNIQUE(FILTER(Detalhado!B2:B,Detalhado!E2:E=s,' + skuOk + ')))),rows,MAP(sites,LAMBDA(s,COUNTIF(Detalhado!E2:E,s))),pct,IFERROR(found/total,0),minP,MAP(sites,LAMBDA(s,IFERROR(MIN(FILTER(parsedPrice,Detalhado!E2:E=s,' + foundValid + ',parsedPrice>0)),""))),avgP,MAP(sites,LAMBDA(s,IFERROR(AVERAGE(FILTER(parsedPrice,Detalhado!E2:E=s,' + foundValid + ',parsedPrice>0)),""))),maxP,MAP(sites,LAMBDA(s,IFERROR(MAX(FILTER(parsedPrice,Detalhado!E2:E=s,' + foundValid + ',parsedPrice>0)),""))),body,HSTACK(sites,found,total,pct,rows,minP,avgP,maxP),totRow,HSTACK("TOTAL",COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',' + foundValid + ')),COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ')),IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',' + foundValid + '))/COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ')),0),COUNTA(FILTER(Detalhado!E2:E,Detalhado!E2:E<>"")),IFERROR(MIN(FILTER(parsedPrice,' + foundValid + ',parsedPrice>0)),""),IFERROR(AVERAGE(FILTER(parsedPrice,' + foundValid + ',parsedPrice>0)),""),IFERROR(MAX(FILTER(parsedPrice,' + foundValid + ',parsedPrice>0)),"")),VSTACK(body,totRow))';
  const avgCoverage = '=IFERROR(AVERAGE(MAP(SORT(UNIQUE(FILTER(Detalhado!E2:E,Detalhado!E2:E<>""))),LAMBDA(s,IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,Detalhado!E2:E=s,' + foundValid + '))/COUNTUNIQUE(FILTER(Detalhado!B2:B,Detalhado!E2:E=s,' + skuOk + ')),0)))),0)';

  sh.getRange('A1').setValue('🔍  PAINEL — CDP RESULTADOS');
  sh.getRange('A2').setFormula(
    '=IFERROR("Atualizado automaticamente | "&TEXT(INDEX(Historico!E:E,COUNTA(Historico!E:E)),"DD/MM/YYYY HH:MM")&" | KPIs por FOUND_PRICE + has_valid_price","—")'
  );
  sh.getRange('A5').setFormula('=IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ')),0)');
  sh.getRange('C5').setFormula('=IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',' + foundValid + ')),0)');
  sh.getRange('E5').setFormula('=MAX(A5-C5,0)');
  sh.getRange('G5').setFormula('=IFERROR(ROUND(VALUE(INDEX(Historico!F:F,COUNTA(Historico!F:F)))/60,1),0)');
  sh.getRange('A9').setFormula('=IFERROR(TEXT(C5/A5,"0.0%"),"—")');
  sh.getRange('C9').setFormula(avgCoverage);
  sh.getRange('E9').setFormula('=IFERROR(COUNTA(UNIQUE(FILTER(Detalhado!E2:E,Detalhado!E2:E<>""))),0)');
  sh.getRange('G9').setFormula('=IFERROR(COUNTA(Historico!A:A)-1,0)');
  sh.getRange('A11').setFormula(
    '=IFERROR("🔗  Job: "&INDEX(Historico!A:A,COUNTA(Historico!A:A))&"   |   Status: "&INDEX(Historico!G:G,COUNTA(Historico!G:G))&"   |   SKUs Lidos: "&INDEX(Historico!H:H,COUNTA(Historico!H:H))&"   |   Origem: "&INDEX(Historico!B:B,COUNTA(Historico!B:B)),"—")'
  );
  sh.getRange('A16').setFormula(siteTable);
  sh.getRange('A34').setValue('📊  DISTRIBUIÇÃO POR STATUS (SKUs únicos vs linhas Detalhado)');
  sh.getRange('A35:D35').setValues([['Status', 'SKUs únicos', 'Linhas Detalhado', '% dos SKUs']]);
  const statusRows = [
    ['✅  FOUND (preço válido)', '=IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',' + foundValid + ')),0)', '=IFERROR(ROWS(FILTER(Detalhado!G2:G,' + foundValid + ')),0)', '=IFERROR(TEXT(B36/$A$5,"0.0%"),"—")'],
    ['⚠️  SEM PREÇO (NO_PRICE)', '=IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',Detalhado!G2:G="NO_PRICE")),0)', '=IFERROR(COUNTIF(Detalhado!G2:G,"NO_PRICE"),0)', '=IFERROR(TEXT(B37/$A$5,"0.0%"),"—")'],
    ['❌  NÃO ENCONTRADO', '=IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',Detalhado!G2:G="NOT_FOUND")),0)', '=IFERROR(COUNTIF(Detalhado!G2:G,"NOT_FOUND"),0)', '=IFERROR(TEXT(B38/$A$5,"0.0%"),"—")'],
    ['🚫  BLOQUEADO', '=IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',Detalhado!G2:G="BLOCKED")),0)', '=IFERROR(COUNTIF(Detalhado!G2:G,"BLOCKED"),0)', '=IFERROR(TEXT(B39/$A$5,"0.0%"),"—")'],
    ['⏱️  TIMEOUT', '=IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',Detalhado!G2:G="TIMEOUT")),0)', '=IFERROR(COUNTIF(Detalhado!G2:G,"TIMEOUT"),0)', '=IFERROR(TEXT(B40/$A$5,"0.0%"),"—")'],
    ['💥  ERRO', '=IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',Detalhado!G2:G="ERROR")),0)', '=IFERROR(COUNTIF(Detalhado!G2:G,"ERROR"),0)', '=IFERROR(TEXT(B41/$A$5,"0.0%"),"—")'],
    ['⏸️  NÃO CONSULTADO', '=IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',Detalhado!G2:G="NOT_QUERIED")),0)', '=IFERROR(COUNTIF(Detalhado!G2:G,"NOT_QUERIED"),0)', '=IFERROR(TEXT(B42/$A$5,"0.0%"),"—")'],
  ];
  sh.getRange(36, 1, 42, 4).setValues(statusRows);
  sh.getRange('A44').setValue('🔌  FONTE PIPELINE (linhas vs SKUs com preço)');
  sh.getRange('A45:D45').setValues([['Fonte', 'Linhas', 'SKUs c/ Preço', '% linhas c/ preço']]);
  sh.getRange('A46:D47').setValues([
    ['API Diversos', '=IFERROR(COUNTIF(Detalhado!X2:X,"API Diversos"),0)', '=IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',Detalhado!X2:X="API Diversos",' + foundValid + ')),0)', '=IFERROR(TEXT(C46/B46,"0.0%"),"—")'],
    ['WEBSCRAPER', '=IFERROR(COUNTIF(Detalhado!X2:X,"WEBSCRAPER"),0)', '=IFERROR(COUNTUNIQUE(FILTER(Detalhado!B2:B,' + skuOk + ',Detalhado!X2:X="WEBSCRAPER",' + foundValid + ')),0)', '=IFERROR(TEXT(C47/B47,"0.0%"),"—")'],
  ]);
  sh.getRange('A49').setValue('📋  ÚLTIMOS JOBS (Historico)');
  sh.getRange('A50:E50').setValues([['Origem', 'Status', 'SKUs Lidos', 'SKUs c/ Preço', 'Duração (s)']]);
  sh.getRange('A51').setFormula(
    '=IFERROR(QUERY(Historico!A2:J,"select B,G,H,J,F where A is not null order by E desc limit 5",0),"—")'
  );
  sh.getRange('A17:H33').clearContent();
}

function ensureHeaders_(sh, names, after) {
  if (!sh || sh.getLastRow() < 1) return;
  const headers = sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0].map(String);
  const missing = names.filter((n) => headers.indexOf(n) < 0);
  if (!missing.length) return;
  if (after && headers.indexOf(after) >= 0) {
    const at = headers.indexOf(after) + 2;
    sh.insertColumnsAfter(at - 1, missing.length);
    sh.getRange(1, at, 1, at + missing.length - 1).setValues([missing]);
  } else {
    sh.insertColumnsAfter(headers.length, missing.length);
    sh.getRange(1, headers.length + 1, 1, headers.length + missing.length).setValues([missing]);
  }
}
