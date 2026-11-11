// SOURCE-ONLY unit regressions. No HTTP request, token, release or provider proof.
import test from 'node:test';
import assert from 'node:assert/strict';
import {
  REPOSITORY, OWNER, WORKFLOW, INPUT, OUTPUT, validateContext, safeUrl, validateApiUrl,
  validateStorageRedirect, validateBrowserUrl, privacyStatus, decodeJson,
  validateRelease, validateAsset, buildProof, summarizeReport,
} from './canary.mjs';
import { createHash } from 'node:crypto';

const SHA = 'a'.repeat(40);
const hash = bytes => createHash('sha256').update(bytes).digest('hex');
const env = () => ({
  GITHUB_ACTIONS: 'true', CI: 'true', RUNNER_ENVIRONMENT: 'github-hosted', RUNNER_OS: 'Linux',
  GITHUB_REPOSITORY: REPOSITORY, GITHUB_REPOSITORY_OWNER: OWNER,
  GITHUB_REPOSITORY_ID: '123456', GITHUB_ACTOR: OWNER, GITHUB_TRIGGERING_ACTOR: OWNER,
  GITHUB_EVENT_NAME: 'workflow_dispatch', GITHUB_REF: 'refs/heads/main', GITHUB_REF_TYPE: 'branch',
  GITHUB_WORKFLOW_REF: WORKFLOW, GITHUB_SHA: SHA, GITHUB_WORKFLOW_SHA: SHA,
  NSP_REPOSITORY_PRIVATE: 'false', GITHUB_RUN_ID: '98765', GITHUB_RUN_ATTEMPT: '1',
});
const api = 'https://api.github.com/repos/' + REPOSITORY;
const upload = 'https://uploads.github.com/repos/' + REPOSITORY;
const expected = { id: 10, tag: 'private-staging-canary-unit-fixture', title: 'DO NOT PUBLISH', reviewed: SHA };
const release = () => ({ id: 10, draft: true, published_at: null, tag_name: expected.tag,
  target_commitish: SHA, name: expected.title, url: api + '/releases/10' });
const spec = { name: 'synthetic-input-v1.txt', bytes: INPUT };
const asset = () => ({ id: 11, name: spec.name, size: INPUT.length, state: 'uploaded',
  url: api + '/releases/assets/11', digest: 'sha256:' + hash(INPUT),
  browser_download_url: 'https://github.com/' + REPOSITORY + '/releases/download/untagged-unit/' + spec.name });

test('SOURCE_ONLY: exact trusted-main hosted context accepted without reading a token', () => {
  const c = validateContext(env(), SHA, 'linux');
  assert.equal(c.repositoryId, 123456);
  assert.equal(c.reviewed, SHA);
});
test('SOURCE_ONLY: every required context field refuses mismatch or absence', () => {
  for (const name of Object.keys(env())) {
    for (const value of [undefined, 'UNTRUSTED']) {
      const e = env(); e[name] = value;
      assert.throws(() => validateContext(e, SHA, 'linux'), { name: 'Error' }, name);
    }
  }
});
test('SOURCE_ONLY: local Windows/non-hosted route and malformed reviewed SHA refused', () => {
  assert.throws(() => validateContext(env(), SHA, 'win32'), /not_linux/);
  for (const sha of ['a'.repeat(39), 'A'.repeat(40), SHA + ';echo', ''])
    assert.throws(() => validateContext(env(), sha, 'linux'), /reviewed_sha/);
});
test('SOURCE_ONLY: unsafe numeric run/repository identities refused', () => {
  for (const key of ['GITHUB_RUN_ID', 'GITHUB_REPOSITORY_ID']) {
    const e = env(); e[key] = '9007199254740993';
    assert.throws(() => validateContext(e, SHA, 'linux'), /invalid/);
  }
});
test('SOURCE_ONLY: untrusted actor, rerun actor, branch and workflow version refused', () => {
  for (const [key, value] of [
    ['GITHUB_ACTOR', 'outsider'], ['GITHUB_TRIGGERING_ACTOR', 'outsider'],
    ['GITHUB_REF', 'refs/heads/feature'], ['GITHUB_WORKFLOW_SHA', 'b'.repeat(40)],
    ['GITHUB_WORKFLOW_REF', WORKFLOW.replace('@refs/heads/main', '@refs/heads/feature')],
  ]) {
    const e = env(); e[key] = value;
    assert.throws(() => validateContext(e, SHA, 'linux'), /context_mismatch/);
  }
});
test('SOURCE_ONLY: only exact same-repository metadata endpoints are allowed', () => {
  for (const url of [api, api + '/releases/10', api + '/releases/10/assets', api + '/releases/assets/11'])
    assert.equal(validateApiUrl(url, 'GET').origin, 'https://api.github.com');
  assert.equal(validateApiUrl(api + '/releases', 'POST').pathname, '/repos/' + REPOSITORY + '/releases');
});
test('SOURCE_ONLY: no publish/edit/delete/tag/arbitrary-host write route', () => {
  for (const [url, method] of [
    [api + '/releases/10', 'PATCH'], [api + '/releases/10', 'DELETE'],
    [api + '/git/refs', 'POST'], [api + '/releases/latest', 'GET'],
    ['https://api.github.com/repos/other/repo/releases', 'POST'],
    ['https://api.github.com.evil.test/repos/' + REPOSITORY + '/releases', 'POST'],
  ]) assert.throws(() => validateApiUrl(url, method), /allowlisted/);
});
test('SOURCE_ONLY: asset uploads allow only the three synthetic contract filenames', () => {
  for (const name of ['synthetic-input-v1.txt', 'synthetic-output-v1.txt', 'CANARY_PROOF.json'])
    assert.doesNotThrow(() => validateApiUrl(upload + '/releases/10/assets?name=' + name, 'POST'));
  for (const tail of ['?name=private.mp4', '?name=synthetic-input-v1.txt&other=1', '?name=../CANARY_PROOF.json', ''])
    assert.throws(() => validateApiUrl(upload + '/releases/10/assets' + tail, 'POST'));
});
test('SOURCE_ONLY: HTTPS/userinfo/port/fragment/invalid URL restrictions', () => {
  for (const raw of ['http://api.github.com', 'https://user:password@api.github.com',
    'https://api.github.com:8443', 'https://api.github.com/#fragment', 'not a url'])
    assert.throws(() => safeUrl(raw));
});
test('SOURCE_ONLY: only bounded GitHub storage redirect targets accepted', () => {
  const source = api + '/releases/assets/11';
  assert.equal(validateStorageRedirect('https://release-assets.githubusercontent.com/a?temporary=fixture', source, 1).hostname,
    'release-assets.githubusercontent.com');
  assert.doesNotThrow(() => validateStorageRedirect('https://objects.githubusercontent.com/a', source, 3));
  for (const raw of ['https://attacker.test/a', 'https://api.github.com/a',
    'https://github.com/other/repo', 'http://release-assets.githubusercontent.com/a',
    'https://u:p@release-assets.githubusercontent.com/a'])
    assert.throws(() => validateStorageRedirect(raw, source, 1));
  assert.throws(() => validateStorageRedirect('https://objects.githubusercontent.com/a', source, 4), /limit/);
  assert.throws(() => validateStorageRedirect('https://objects.githubusercontent.com/a', 'https://evil.test/a', 1), /origin/);
});
test('SOURCE_ONLY: browser asset URLs bind exact repo, HTTPS and filename', () => {
  assert.doesNotThrow(() => validateBrowserUrl(asset().browser_download_url, spec.name));
  for (const raw of [asset().browser_download_url + '?signed=fixture',
    asset().browser_download_url.replace(REPOSITORY, 'other/repo'),
    asset().browser_download_url.replace(spec.name, 'private.mp4')])
    assert.throws(() => validateBrowserUrl(raw, spec.name));
});
test('SOURCE_ONLY: only affirmative 401/404 proves anonymous denial', () => {
  for (const code of [401, 404]) assert.equal(privacyStatus(code), code);
  for (const code of [undefined, null, 0, 200, 201, 206, 301, 302, 307, 403, 429, 500, 503])
    assert.throws(() => privacyStatus(code), /not_proven/);
});
test('SOURCE_ONLY: bounded JSON rejects malformed, invalid UTF8 and primitive bodies', () => {
  assert.deepEqual(decodeJson(Buffer.from('{"draft":true}')), { draft: true });
  assert.deepEqual(decodeJson(Buffer.from('[]')), []);
  for (const bytes of [Buffer.from('{"unfinished":'), Buffer.from([0xc3, 0x28]), Buffer.from('null'),
    Buffer.from('"a"'), Buffer.alloc(65537, 32)]) assert.throws(() => decodeJson(bytes));
});
test('SOURCE_ONLY: draft identity rejects publication, wrong owner, tag or target', () => {
  assert.equal(validateRelease(release(), expected).id, 10);
  for (const [key, value] of [['draft', false], ['published_at', '2026-11-11T00:00:00Z'],
    ['id', 99], ['url', 'https://api.github.com/repos/other/repo/releases/10'],
    ['tag_name', 'published'], ['target_commitish', 'main'], ['name', 'Other']]) {
    const r = release(); r[key] = value;
    assert.throws(() => validateRelease(r, expected));
  }
});
test('SOURCE_ONLY: upload metadata must match actual fixed bytes/digest and owner', () => {
  assert.equal(validateAsset(asset(), spec).id, 11);
  for (const [key, value] of [['id', 0], ['name', 'private.mp4'], ['size', INPUT.length + 1],
    ['state', 'starter'], ['digest', 'sha256:' + '0'.repeat(64)],
    ['url', 'https://api.github.com/repos/other/repo/releases/assets/11']]) {
    const a = asset(); a[key] = value;
    assert.throws(() => validateAsset(a, spec));
  }
});

function proofFixture() {
  return { repositoryId: 123456, observations: [
    { check: 'repository_identity_verified', pass: true },
    { check: 'draft_unpublished', pass: true },
    { check: 'synthetic-input-v1.txt_authenticated_roundtrip', pass: true },
    { check: 'synthetic-output-v1.txt_authenticated_roundtrip', pass: true },
    ...['final_release_metadata', 'final_synthetic-input-v1.txt_asset_api',
      'final_synthetic-input-v1.txt_browser', 'final_synthetic-output-v1.txt_asset_api',
      'final_synthetic-output-v1.txt_browser'].map(check => ({ check, denied: true, status: 404 })),
  ] };
}
test('SOURCE_ONLY: proof assembly binds observed synthetic fixture without self-ID recursion', () => {
  const p = buildProof(proofFixture(), validateContext(env(), SHA, 'linux'), expected, { id: 11 }, { id: 12 });
  assert.equal(p.schema, 'northstar.private-media-canary.v1');
  assert.equal(p.source_sha, SHA);
  assert.equal(p.workflow_run_id, 98765);
  assert.equal(p.workflow_run_attempt, 1);
  assert.equal(p.source_workflow_path, '.github/workflows/private-media-canary.yml');
  assert.equal(p.private_media_uploaded, false);
  assert.equal(Object.keys(p.checks).length, 9);
  assert.ok(Object.values(p.checks).every(value => value === true));
  assert.equal(p.canary_input.sha256, hash(INPUT));
  assert.equal(p.canary_output.sha256, hash(OUTPUT));
  assert.equal('proof_asset_id' in p, false);
});
test('SOURCE_ONLY: missing/failed/ambiguous proof observations never become success', () => {
  const c = validateContext(env(), SHA, 'linux');
  const missing = proofFixture(); missing.observations.pop();
  assert.throws(() => buildProof(missing, c, expected, { id: 11 }, { id: 12 }), /incomplete/);
  const failed = proofFixture(); failed.observations[4].status = 200;
  assert.throws(() => buildProof(failed, c, expected, { id: 11 }, { id: 12 }), /incomplete/);
  const duplicate = proofFixture(); duplicate.observations.push({ ...duplicate.observations[2] });
  assert.throws(() => buildProof(duplicate, c, expected, { id: 11 }, { id: 12 }), /incomplete/);
  const changedDraft = proofFixture(); changedDraft.observations.push({ check: 'draft_unpublished', pass: false });
  assert.throws(() => buildProof(changedDraft, c, expected, { id: 11 }, { id: 12 }), /incomplete/);
});

test('SOURCE_ONLY: an ambiguous failure retains recovery tag and known IDs without a pass', () => {
  const r = summarizeReport({
    status: 'FAILED_OR_INCOMPLETE_PRIVACY_NOT_PROVEN', providerProof: false,
    repositoryId: 123456, releaseId: null, stagingTag: 'private-staging-canary-unit-fixture',
    assetIds: [], reviewedSha: SHA, runId: '98765', attempt: '1',
    errors: ['network_or_timeout_not_privacy_proof'],
  });
  assert.equal(r.providerProof, false);
  assert.equal(r.draft_release_id, null);
  assert.equal(r.staging_tag, 'private-staging-canary-unit-fixture');
  assert.equal(r.proof_asset_id, null);
  assert.deepEqual(r.errors, ['network_or_timeout_not_privacy_proof']);
  assert.equal(r.private_media_uploaded, false);
});

test('SOURCE_ONLY: 403 throttling or abuse refusal is inconclusive and cannot sign a proof', () => {
  assert.throws(() => privacyStatus(403), /not_proven_denied_status_403/);
  for (let i = 4; i < 9; i++) {
    const r = proofFixture();
    r.observations[i] = { ...r.observations[i], status: 403, denied: true };
    assert.throws(() => buildProof(r, validateContext(env(), SHA, 'linux'), expected, { id: 11 }, { id: 12 }),
      /incomplete/);
  }
});
