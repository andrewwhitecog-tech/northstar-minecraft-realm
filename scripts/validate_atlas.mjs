import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const begin = '<!-- atlas:begin -->';
const end = '<!-- atlas:end -->';
const text = (value, label) => { if (typeof value !== 'string' || !value.trim()) throw Error(label + ' must be nonempty text'); };
const integer = (value, label) => { if (!Number.isSafeInteger(value)) throw Error(label + ' must be an integer'); };
function position(value, nullableHeight, label) {
  if (!Array.isArray(value) || value.length !== 3) throw Error(label + ' must have three coordinates');
  value.forEach((v, i) => { if (!(nullableHeight && i === 1 && v === null)) integer(v, label + '[' + i + ']'); });
}
export function validateAtlas(atlas) {
  text(atlas.server_name, 'server_name');
  for (const key of ['website', 'mirror_guide']) { const url = new URL(atlas[key]); if (url.protocol !== 'https:') throw Error(key + ' must use HTTPS'); }
  for (const key of ['java_edition', 'bedrock_edition']) {
    const conn = atlas.connection?.[key]; if (!conn) throw Error('Missing ' + key);
    text(conn.address, key + '.address'); integer(conn.port, key + '.port');
    if (conn.port < 1 || conn.port > 65535) throw Error('Invalid connection port');
  }
  const bedrock = atlas.connection.bedrock_edition;
  if (bedrock.quick_add_uri !== 'minecraft://?addExternalServer=NorthStar|' + bedrock.address + ':' + bedrock.port) throw Error('Bedrock quick-add disagrees with address or port');
  text(atlas.connection.java_edition.version, 'java version');
  text(atlas.connection.xbox_console?.xbox_gamertag, 'Xbox gamertag');
  if (!Array.isArray(atlas.in_world_commands_and_events) || !atlas.in_world_commands_and_events.length) throw Error('Missing commands');
  for (const command of atlas.in_world_commands_and_events) for (const key of ['name', 'usage', 'description']) text(command[key], 'command.' + key);
  if (!atlas.landmarks || Array.isArray(atlas.landmarks) || typeof atlas.landmarks !== 'object' || !Object.keys(atlas.landmarks).length) throw Error('Missing landmarks');
  for (const [id, landmark] of Object.entries(atlas.landmarks)) {
    if (!/^[a-z][a-z0-9_]*$/.test(id)) throw Error('Invalid landmark id: ' + id);
    text(landmark.name, id + '.name'); text(landmark.seen, id + '.seen');
    position(landmark.pos, true, id + '.pos'); position(landmark.lookAt, false, id + '.lookAt');
    integer(landmark.range, id + '.range'); if (landmark.range <= 0) throw Error(id + '.range must be positive');
    if ('refuge' in landmark && typeof landmark.refuge !== 'boolean') throw Error(id + '.refuge must be boolean');
    if (/[|\r\n]/.test(landmark.name)) throw Error(id + '.name cannot break the Markdown table');
  }
}

function guideSection(readme, title) {
  const headings = [...readme.matchAll(/^#{1,3} [^\r\n]+/gm)];
  const matching = headings.filter(heading => {
    const name = heading[0].replace(/^#{1,3} (?:\d+\. )?/, '');
    return name === title || name.startsWith(title + ' (');
  });
  if (matching.length !== 1) throw Error('README needs exactly one ' + title + ' quick-guide section');
  const heading = matching[0];
  const start = heading.index + heading[0].length;
  const next = headings.find(item => item.index > heading.index);
  return readme.slice(start, next ? next.index : undefined);
}
function guideLine(section, prefix, label) {
  const lines = section.split(/\r?\n/).filter(line => line.startsWith(prefix));
  if (lines.length !== 1) throw Error('README ' + label + ' must appear exactly once');
  return lines[0].slice(prefix.length).trim();
}
function guideCode(value, label) {
  const pieces = value.split(String.fromCharCode(96));
  if (pieces.length !== 3 || pieces[0] !== '' || !pieces[1]) throw Error('README ' + label + ' needs one code-formatted value');
  return pieces[1];
}
export function validateReadme(readme, atlas) {
  validateAtlas(atlas);
  const java = guideSection(readme, 'Minecraft Java Edition');
  const bedrock = guideSection(readme, 'Minecraft Bedrock Edition');
  const xbox = guideSection(readme, 'Xbox Series X|S & Xbox One');
  for (const [section, connection, label] of [
    [java, atlas.connection.java_edition, 'Java'],
    [bedrock, atlas.connection.bedrock_edition, 'Bedrock'],
  ]) {
    for (const [field, key] of [['Server Address', 'address'], ['Port', 'port']]) {
      const value = guideCode(guideLine(section, '- **' + field + ':**', label + ' ' + field), label + ' ' + field);
      if (value !== String(connection[key])) throw Error('README ' + label + ' ' + field + ' disagrees with atlas');
    }
  }
  const version = guideLine(java, '- **Client Version:**', 'Java client version');
  if (!version.startsWith('Release ') || guideCode(version.slice(8), 'Java client version') !== atlas.connection.java_edition.version.split(/[\s(]/)[0]) throw Error('README Java client version disagrees with atlas');
  const launch = guideLine(bedrock, '- **One-Click Launch:**', 'Bedrock quick-add');
  const launchParts = launch.split(String.fromCharCode(96));
  if (launchParts.length !== 3 || launchParts[1] !== atlas.connection.bedrock_edition.quick_add_uri) throw Error('README Bedrock quick-add disagrees with atlas');
  for (const [prefix, label] of [['1. Add Xbox gamertag **', 'Xbox gamertag'], ['3. Select **', 'Xbox selection gamertag']]) {
    const gamertag = guideCode(guideLine(xbox, prefix, label), label);
    if (gamertag !== atlas.connection.xbox_console.xbox_gamertag) throw Error('README ' + label + ' disagrees with atlas');
  }
}

export function renderTable(atlas) {
  validateAtlas(atlas);
  const coord = v => v.map(n => n === null ? '—' : n).join(', ');
  const tick = String.fromCharCode(96);
  const rows = ['| Landmark ID | Name | Position (' + tick + 'X, Y, Z' + tick + ') | Look at |', '| :--- | :--- | :--- | :--- |'];
  for (const [id, item] of Object.entries(atlas.landmarks)) {
    const name = item.name.replace(/^the /i, '').replace(/^./, c => c.toUpperCase());
    rows.push('| ' + tick + id + tick + ' | ' + name + ' | ' + tick + coord(item.pos) + tick + ' | ' + tick + coord(item.lookAt) + tick + ' |');
  }
  return rows.join('\n');
}
export function updateReadme(readme, atlas) {
  if (readme.split(begin).length !== 2 || readme.split(end).length !== 2 || readme.indexOf(end) < readme.indexOf(begin)) throw Error('README needs exactly one ordered atlas marker pair');
  return readme.slice(0, readme.indexOf(begin) + begin.length) + '\n' + renderTable(atlas) + '\n' + readme.slice(readme.indexOf(end));
}
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const atlas = JSON.parse(fs.readFileSync(path.join(root, 'WORLD_ATLAS.json'), 'utf8'));
  const file = path.join(root, 'README.md'); const original = fs.readFileSync(file, 'utf8').replaceAll('\r\n', '\n');
  const updated = updateReadme(original, atlas);
  validateReadme(updated, atlas);
  if (process.argv.includes('--write')) fs.writeFileSync(file, updated);
  else if (updated !== original) throw Error('README atlas table is stale. Run node scripts/validate_atlas.mjs --write');
  console.log('Validated atlas and README for ' + Object.keys(atlas.landmarks).length + ' landmarks. This checks source consistency, not live gameplay.');
}
