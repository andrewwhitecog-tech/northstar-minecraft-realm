import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { spawnSync } from 'node:child_process';
const readme = fs.readFileSync(new URL('../README.md', import.meta.url), 'utf8');
const atlas = JSON.parse(fs.readFileSync(new URL('../WORLD_ATLAS.json', import.meta.url), 'utf8'));
const script = fs.readFileSync(new URL('../scripts/validate_atlas.mjs', import.meta.url), 'utf8');
function check(t, mutate) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'nsp-atlas-join-'));
  t.after(() => fs.rmSync(dir, { recursive: true, force: true }));
  const input = { atlas: structuredClone(atlas), readme };
  mutate(input);
  fs.mkdirSync(path.join(dir, 'scripts'));
  fs.writeFileSync(path.join(dir, 'scripts/validate_atlas.mjs'), script);
  fs.writeFileSync(path.join(dir, 'WORLD_ATLAS.json'), JSON.stringify(input.atlas));
  fs.writeFileSync(path.join(dir, 'README.md'), input.readme);
  return spawnSync(process.execPath, [path.join(dir, 'scripts/validate_atlas.mjs')], { encoding: 'utf8', windowsHide: true, timeout: 5000 });
}
function refused(result, reason) {
  assert.equal(result.error, undefined);
  assert.notEqual(result.status, 0, 'stale join instructions must fail the real CLI');
  assert.match(result.stderr, reason);
}
test('current join guide passes the real CLI', t => {
  const result = check(t, () => {});
  assert.equal(result.error, undefined);
  assert.equal(result.status, 0, result.stderr);
});
test('a changed Java address cannot leave the join guide stale', t => {
  refused(check(t, x => { x.atlas.connection.java_edition.address = 'java.example'; }), /Java Server Address disagrees/);
});
test('a changed Java port cannot leave the join guide stale', t => {
  refused(check(t, x => { x.atlas.connection.java_edition.port = 25566; }), /Java Port disagrees/);
});
test('a changed Java version cannot leave the join guide stale', t => {
  refused(check(t, x => { x.atlas.connection.java_edition.version = '26.4 (zero client mods required)'; }), /Java client version disagrees/);
});
test('a valid changed Bedrock endpoint cannot leave the join guide stale', t => {
  refused(check(t, x => {
    const b = x.atlas.connection.bedrock_edition;
    b.address = 'bedrock.example'; b.port = 25131;
    b.quick_add_uri = 'minecraft://?addExternalServer=NorthStar|bedrock.example:25131';
  }), /Bedrock Server Address disagrees/);
});
test('a changed Bedrock port cannot leave the join guide stale', t => {
  refused(check(t, x => {
    const b = x.atlas.connection.bedrock_edition; b.port = 25131;
    b.quick_add_uri = 'minecraft://?addExternalServer=NorthStar|' + b.address + ':25131';
  }), /Bedrock Port disagrees/);
});
test('a wrong quick-add link in README is refused', t => {
  refused(check(t, x => { x.readme = x.readme.replace(x.atlas.connection.bedrock_edition.quick_add_uri, 'minecraft://?addExternalServer=NorthStar|wrong.example:25130'); }), /Bedrock quick-add disagrees/);
});
test('a changed Xbox gamertag cannot leave the friend step stale', t => {
  refused(check(t, x => { x.atlas.connection.xbox_console.xbox_gamertag = 'NewFriend'; }), /Xbox gamertag disagrees/);
});
test('a stale Xbox selection step is refused', t => {
  refused(check(t, x => { x.readme = x.readme.replace('3. Select **`UncleVorath`**', '3. Select **`WrongFriend`**'); }), /Xbox selection gamertag disagrees/);
});
test('missing or duplicate address fields and guide sections are refused', t => {
  for (const replacement of ['', '- **Server Address:** `play.northstarprime.net`\n- **Server Address:** `play.northstarprime.net`']) {
    refused(check(t, x => { x.readme = x.readme.replace('- **Server Address:** `play.northstarprime.net`', replacement); }), /Java Server Address must appear exactly once/);
  }
  refused(check(t, x => { x.readme = x.readme.replace('### 1. Minecraft Java Edition (26.3)', '### 1. Missing Java Guide'); }), /exactly one Minecraft Java Edition/);
  refused(check(t, x => { x.readme += '\n### Minecraft Java Edition (26.3)\n- **Server Address:** `wrong.example`\n- **Port:** `25565`\n'; }), /exactly one Minecraft Java Edition/);
});
test('updating both connection sources passes without rewriting historical notes', t => {
  const result = check(t, x => {
    x.atlas.connection.java_edition.port = 25566;
    x.readme = x.readme.replace('- **Port:** `25565` (default)', '- **Port:** `25566` (default)');
    x.atlas.connection.xbox_console.xbox_gamertag = 'NewFriend';
    x.readme = x.readme.replace('1. Add Xbox gamertag **`UncleVorath`**', '1. Add Xbox gamertag **`NewFriend`**').replace('3. Select **`UncleVorath`**', '3. Select **`NewFriend`**');
  });
  assert.equal(result.error, undefined);
  assert.equal(result.status, 0, result.stderr);
});
