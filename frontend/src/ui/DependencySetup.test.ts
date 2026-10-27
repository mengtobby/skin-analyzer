// @vitest-environment node
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { expect, it, vi } from 'vitest';

const manifest = JSON.parse(readFileSync(new URL('../../package.json', import.meta.url), 'utf8')) as { scripts: { prebuild: string } };
const command = manifest.scripts.prebuild;
const script = command.slice('node -e "'.length, -1);

function runSetup(installed: boolean, status = 0) {
  const spawnSync = vi.fn(() => ({ status }));
  const exit = vi.fn();
  const resolve = vi.fn(() => {
    if (!installed) throw Object.assign(new Error('Font package missing'), { code: 'MODULE_NOT_FOUND' });
    return '/dependencies/urbanist/index.css';
  });
  const loader = Object.assign(vi.fn(() => ({ spawnSync })), { resolve });
  runInNewContext(script, { require: loader, process: { execPath: 'node', env: { npm_execpath: 'npm-cli.js' }, exit } });
  return { spawnSync, exit };
}

it('does not install or contact the registry when the bundled font dependency is present', () => {
  const { spawnSync, exit } = runSetup(true);
  expect(spawnSync).not.toHaveBeenCalled();
  expect(exit).not.toHaveBeenCalled();
});
it('installs the pinned missing font before the unchanged build checks', () => {
  const { spawnSync, exit } = runSetup(false);
  expect(spawnSync).toHaveBeenCalledWith('node', expect.arrayContaining(['npm-cli.js', 'install', '--ignore-scripts', '--no-save', '--package-lock=false', '@fontsource-variable/urbanist@5.3.0']), { stdio: 'inherit' });
  expect(exit).toHaveBeenCalledWith(0);
});
it('propagates dependency installation failure instead of skipping build checks', () => {
  expect(runSetup(false, 1).exit).toHaveBeenCalledWith(1);
});
