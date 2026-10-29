// Use the credential for the exact project already pulled by `vercel pull`.
// Never create, rotate, print, or persist an automation credential here.
import {readFileSync} from 'node:fs';
import {parseEnv} from 'node:util';
import {spawnSync} from 'node:child_process';

const values = parseEnv(readFileSync('.vercel/.env.production.local', 'utf8'));
const projectCredential = values.VERCEL_AUTOMATION_BYPASS_SECRET;
const credential = projectCredential || process.env.VERCEL_AUTOMATION_BYPASS_SECRET;
if (!credential) {
  throw new Error('No existing automation credential is available for staged validation. Protection settings were not changed.');
}
console.log(projectCredential
  ? 'Staged validation uses the existing project credential from vercel pull.'
  : 'Staged validation uses the existing GitHub automation credential.');
const result = spawnSync('python3', ['-B', 'tests/deployment/smoke.py', ...process.argv.slice(2)], {
  env: {...process.env, VERCEL_AUTOMATION_BYPASS_SECRET: credential},
  stdio: 'inherit',
});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
