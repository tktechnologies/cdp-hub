#!/usr/bin/env node
/**
 * Convert n8n workflow export JSON (repo or MCP dump) to Workflow SDK source.
 *
 * Usage:
 *   node scripts/n8n_workflow_json_to_sdk.mjs <workflow.json> [--workflow-id ID]
 */
import fs from 'node:fs';

const [, , inputPath, ...flags] = process.argv;
const idFlag = flags.find((f) => f.startsWith('--workflow-id='));
const forcedId = idFlag ? idFlag.split('=')[1] : null;

if (!inputPath) {
  console.error('Usage: node scripts/n8n_workflow_json_to_sdk.mjs <workflow.json> [--workflow-id ID]');
  process.exit(1);
}

const raw = JSON.parse(fs.readFileSync(inputPath, 'utf8'));
const wf = raw.workflow ?? raw;
const nameFlag = flags.find((f) => f.startsWith('--workflow-name='));
const workflowId = forcedId ?? wf.id;
const workflowName = nameFlag?.split('=')[1] ?? wf.name ?? 'workflow';

if (!workflowId || !wf.nodes?.length) {
  console.error('Invalid workflow JSON: missing id or nodes');
  process.exit(1);
}

const byName = Object.fromEntries(wf.nodes.map((n) => [n.name, n]));
const connections = wf.connections ?? {};
const parallelAdds = [];

const slugFor = {};
const slugUsed = new Set();
for (const n of wf.nodes) {
  const baseRaw = String(n.name)
    .replace(/[^a-zA-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
  let base = /^[0-9]/.test(baseRaw) ? `_${baseRaw}` : baseRaw;
  let s = base;
  let i = 2;
  while (slugUsed.has(s)) {
    s = `${base}_${i++}`;
  }
  slugUsed.add(s);
  slugFor[n.name] = s;
}

function slug(name) {
  if (slugFor[name]) return slugFor[name];
  const base = String(name)
    .replace(/[^a-zA-Z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
  return /^[0-9]/.test(base) ? `_${base}` : base;
}

function configPayload(n) {
  const cfg = {
    name: n.name,
    parameters: n.parameters,
    position: n.position,
  };
  if (n.alwaysOutputData === true) cfg.alwaysOutputData = true;
  if (n.executeOnce === true) cfg.executeOnce = true;
  if (n.onError) cfg.onError = n.onError;
  if (n.notes) cfg.notes = n.notes;
  return cfg;
}

function emitNodeDecl(n) {
  const cfg = configPayload(n);
  const cfgJson = JSON.stringify(cfg, null, 2);
  if (n.type === 'n8n-nodes-base.webhook' || n.type === 'n8n-nodes-base.scheduleTrigger' ||
      n.type === 'n8n-nodes-base.gmailTrigger' || n.type === 'n8n-nodes-base.telegramTrigger' ||
      n.type === 'n8n-nodes-base.manualTrigger' ||
      n.type === 'n8n-nodes-base.executeWorkflowTrigger') {
    const extra = n.webhookId ? `,\n  webhookId: ${JSON.stringify(n.webhookId)}` : '';
    return `const ${slug(n.name)} = trigger({
  type: ${JSON.stringify(n.type)},
  version: ${JSON.stringify(n.typeVersion)},
  config: ${cfgJson}${extra ? '' : ''},
  output: [{}],
});`;
  }
  if (n.type === 'n8n-nodes-base.if') {
    return `const ${slug(n.name)} = ifElse({
  version: ${JSON.stringify(n.typeVersion)},
  config: ${cfgJson},
});`;
  }
  if (n.type === 'n8n-nodes-base.switch') {
    return `const ${slug(n.name)} = switchCase({
  version: ${JSON.stringify(n.typeVersion)},
  config: ${cfgJson},
});`;
  }
  return `const ${slug(n.name)} = node({
  type: ${JSON.stringify(n.type)},
  version: ${JSON.stringify(n.typeVersion)},
  config: ${cfgJson},
  output: [{}],
});`;
}

function buildChain(nodeName, visiting = new Set()) {
  if (!nodeName || !byName[nodeName]) return slug(nodeName);
  if (visiting.has(nodeName)) return slug(nodeName);
  visiting.add(nodeName);

  const n = byName[nodeName];
  const main = connections[nodeName]?.main ?? [];

  if (n.type === 'n8n-nodes-base.if') {
    const trueOuts = main[0] ?? [];
    const falseOuts = main[1] ?? [];
    if (trueOuts.length > 1) {
      parallelAdds.push({ source: nodeName, targets: trueOuts.map((o) => o.node) });
    }
    if (falseOuts.length > 1) {
      parallelAdds.push({ source: nodeName, targets: falseOuts.map((o) => o.node) });
    }
    const t = trueOuts[0]?.node;
    const f = falseOuts[0]?.node;
    const tChain = t ? buildChain(t, new Set(visiting)) : slug(nodeName);
    const fChain = f ? buildChain(f, new Set(visiting)) : slug(nodeName);
    if (t && f) return `${slug(nodeName)}.onTrue(${tChain}).onFalse(${fChain})`;
    if (t) return `${slug(nodeName)}.onTrue(${tChain})`;
    if (f) return `${slug(nodeName)}.onFalse(${fChain})`;
    return slug(nodeName);
  }

  if (n.type === 'n8n-nodes-base.switch') {
    const parts = [];
    for (let i = 0; i < main.length; i += 1) {
      const target = main[i]?.[0]?.node;
      if (!target) continue;
      const chain = buildChain(target, new Set(visiting));
      parts.push(`.onCase(${i}, ${chain})`);
    }
    if (!parts.length) return slug(nodeName);
    return `${slug(nodeName)}${parts.join('')}`;
  }

  const outs = main[0] ?? [];
  if (!outs.length) return slug(nodeName);
  if (outs.length > 1) {
    parallelAdds.push({ source: nodeName, targets: outs.map((o) => o.node) });
  }
  const first = outs[0].node;
  return `${slug(nodeName)}.to(${buildChain(first, visiting)})`;
}

const triggerTypes = new Set([
  'n8n-nodes-base.webhook',
  'n8n-nodes-base.scheduleTrigger',
  'n8n-nodes-base.gmailTrigger',
  'n8n-nodes-base.telegramTrigger',
  'n8n-nodes-base.manualTrigger',
  'n8n-nodes-base.executeWorkflowTrigger',
]);

const triggers = wf.nodes.filter((n) => triggerTypes.has(n.type));
if (!triggers.length) {
  console.error('No trigger nodes found');
  process.exit(1);
}

function firstTarget(triggerName) {
  return connections[triggerName]?.main?.[0]?.[0]?.node;
}

const lines = [];
lines.push(`import { workflow, node, trigger, ifElse, switchCase } from '@n8n/workflow-sdk';\n`);
for (const n of wf.nodes) {
  lines.push(emitNodeDecl(n));
  lines.push('');
}

const builder = [];
for (const tr of triggers) {
  const first = firstTarget(tr.name);
  if (!first) {
    builder.push(`.add(${slug(tr.name)})`);
    continue;
  }
  builder.push(`.add(${slug(tr.name)}).to(${buildChain(first)})`);
}

const parallelSeen = new Set();
for (const { source, targets } of parallelAdds) {
  for (let i = 1; i < targets.length; i += 1) {
    const key = `${source}::${targets[i]}`;
    if (parallelSeen.has(key)) continue;
    parallelSeen.add(key);
    builder.push(`.add(${slug(source)}).to(${buildChain(targets[i])})`);
  }
}

lines.push(`export default workflow(${JSON.stringify(workflowId)}, ${JSON.stringify(workflowName)})`);
lines.push(`  ${builder.join('\n  ')};`);

process.stdout.write(lines.join('\n'));
