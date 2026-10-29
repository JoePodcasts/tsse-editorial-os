// Use the credential for the exact project already pulled by `vercel pull`.
// Never create, rotate, print, or persist an automation credential here.
import {readFileSync} from 'node:fs';
import {parseEnv} from 'node:util';
import {spawnSync} from 'node:child_process';

const values = parseEnv(readFileSync('.vercel/.env.production.local', 'utf8'));
let projectCredential = values.VERCEL_AUTOMATION_BYPASS_SECRET;
if (!projectCredential && process.env.VERCEL_TOKEN) {
  // Match the CLI's existing automation-bypass selection, but never its
  // create-if-missing behavior. Keep the project response entirely in memory.
  const {VERCEL_PROJECT_ID: projectId, VERCEL_ORG_ID: teamId} = process.env;
  if (!projectId || !teamId) throw new Error('Missing linked project identity.');
  const response = await fetch(`https://api.vercel.com/v9/projects/${encodeURIComponent(projectId)}?teamId=${encodeURIComponent(teamId)}`, {
    headers: {Authorization: `Bearer ${process.env.VERCEL_TOKEN}`},
    redirect: 'error', signal: AbortSignal.timeout(30000),
  });
  if (!response.ok) throw new Error(`Project authentication lookup failed (HTTP ${response.status}).`);
  const project = await response.json();
  if (project.id !== projectId || project.accountId !== teamId) throw new Error('Project identity mismatch.');
  projectCredential = Object.entries(project.protectionBypass || {})
    .find(([, metadata]) => metadata.scope === 'automation-bypass')?.[0];
  if (!projectCredential) throw new Error('The linked project has no existing automation credential. No access controls were changed.');
}
const credential = projectCredential || process.env.VERCEL_AUTOMATION_BYPASS_SECRET;
if (!credential) {
  throw new Error('No existing automation credential is available for staged validation. Protection settings were not changed.');
}
console.log(projectCredential
  ? 'Staged validation uses the existing credential for the linked Vercel project.'
  : 'Staged validation uses the existing GitHub automation credential.');
const childEnv = {...process.env, VERCEL_AUTOMATION_BYPASS_SECRET: credential};
delete childEnv.VERCEL_TOKEN;
const result = spawnSync('python3', ['-B', 'tests/deployment/smoke.py', ...process.argv.slice(2)], {
  env: childEnv,
  stdio: 'inherit',
});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
