// Check the actual production runtime credential pulled by Vercel, without
// printing or copying it into a build artifact. The build's GITHUB_TOKEN alone
// cannot prove that a deployed function can read later no-change syncs.
import {readFileSync} from 'node:fs';
import {parseEnv} from 'node:util';
import {spawnSync} from 'node:child_process';

const values = parseEnv(readFileSync('.vercel/.env.production.local', 'utf8'));
if (!values.ARCHIVE_STATUS_TOKEN) {
  throw new Error('Configure ARCHIVE_STATUS_TOKEN in Vercel production with read-only Actions access to JoePodcasts/tsse-editorial-os.');
}
const program = `
import json
import archive_status as status
baseline = json.load(open('vercel_runtime/archive/sync-status.json'))
status.checked(status.retrieve(baseline['archive_fingerprint']), baseline['archive_fingerprint'], baseline['published_episodes'])
print('Production freshness credential verified against the matching successful Actions artifact.')
`;
const result = spawnSync('python3', ['-B', '-c', program], {
  env: {...process.env, ARCHIVE_STATUS_TOKEN: values.ARCHIVE_STATUS_TOKEN},
  stdio: 'inherit',
});
if (result.error) throw result.error;
process.exitCode = result.status ?? 1;
