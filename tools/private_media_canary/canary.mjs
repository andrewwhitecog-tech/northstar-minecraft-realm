import { createHash, randomUUID } from 'node:crypto';
import { writeFile, appendFile } from 'node:fs/promises';
import { pathToFileURL } from 'node:url';

export const REPOSITORY = 'andrewwhitecog-tech/northstar-minecraft-realm';
export const OWNER = 'andrewwhitecog-tech';
export const WORKFLOW = REPOSITORY + '/.github/workflows/private-media-canary.yml@refs/heads/main';
export const INPUT = Buffer.from('NORTHSTAR_SYNTHETIC_CANARY_V1\nHarmless fixed test bytes. No media or private data.\n', 'utf8');
export const OUTPUT = Buffer.from('NORTHSTAR_SYNTHETIC_RESULT_V1\nHarmless fixed output. No media or private data.\n', 'utf8');
const INPUT_NAME = 'synthetic-input-v1.txt';
const OUTPUT_NAME = 'synthetic-output-v1.txt';
const PROOF_NAME = 'CANARY_PROOF.json';
const API = 'https://api.github.com';
const UPLOAD = 'https://uploads.github.com';
const PREFIX = '/repos/' + REPOSITORY;
const MAX_BODY = 65536;
const STORAGE = new Set(['release-assets.githubusercontent.com', 'objects.githubusercontent.com']);
// 403 can mean rate limiting/abuse protection; it is inconclusive, never privacy proof.
const DENIALS = new Set([401, 404]);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
function need(condition, code) { if (!condition) throw new Error(code); }
function id(value) { return Number.isSafeInteger(value) && value > 0; }
function object(value) { return value !== null && typeof value === 'object' && !Array.isArray(value); }

export function validateContext(env, reviewed, platform = process.platform) {
  need(/^[0-9a-f]{40}$/.test(reviewed || ''), 'reviewed_sha_invalid');
  const exact = {
    GITHUB_ACTIONS: 'true', CI: 'true', RUNNER_ENVIRONMENT: 'github-hosted', RUNNER_OS: 'Linux',
    GITHUB_REPOSITORY: REPOSITORY, GITHUB_REPOSITORY_OWNER: OWNER,
    GITHUB_ACTOR: OWNER, GITHUB_TRIGGERING_ACTOR: OWNER,
    GITHUB_EVENT_NAME: 'workflow_dispatch', GITHUB_REF: 'refs/heads/main', GITHUB_REF_TYPE: 'branch',
    GITHUB_WORKFLOW_REF: WORKFLOW, GITHUB_SHA: reviewed, GITHUB_WORKFLOW_SHA: reviewed,
    NSP_REPOSITORY_PRIVATE: 'false',
  };
  need(platform === 'linux', 'host_platform_not_linux');
  for (const [key, value] of Object.entries(exact)) need(env[key] === value, 'context_mismatch_' + key);
  need(/^[1-9][0-9]{0,19}$/.test(env.GITHUB_RUN_ID || '') && id(Number(env.GITHUB_RUN_ID)), 'run_id_invalid');
  need(/^[1-9][0-9]{0,19}$/.test(env.GITHUB_REPOSITORY_ID || '') && id(Number(env.GITHUB_REPOSITORY_ID)), 'repository_id_invalid');
  need(/^[1-9][0-9]{0,4}$/.test(env.GITHUB_RUN_ATTEMPT || ''), 'run_attempt_invalid');
  return { reviewed, runId: env.GITHUB_RUN_ID, attempt: env.GITHUB_RUN_ATTEMPT, repositoryId: Number(env.GITHUB_REPOSITORY_ID) };
}

export function safeUrl(raw) {
  let u;
  try { u = new URL(raw); } catch { throw new Error('url_invalid'); }
  need(u.protocol === 'https:' && !u.username && !u.password && !u.port && !u.hash, 'url_not_clean_https');
  return u;
}

export function validateApiUrl(raw, method) {
  const u = safeUrl(raw);
  const p = u.pathname;
  const release = PREFIX + '/releases';
  const numeric = '[1-9][0-9]*';
  const validGet = p === '/repos/' + REPOSITORY ||
    new RegExp('^' + release + '/' + numeric + '(?:/assets)?$').test(p) ||
    new RegExp('^' + release + '/assets/' + numeric + '$').test(p);
  const validCreate = p === release && !u.search;
  const validUpload = new RegExp('^' + release + '/' + numeric + '/assets$').test(p) &&
    u.searchParams.size === 1 && [INPUT_NAME, OUTPUT_NAME, PROOF_NAME].includes(u.searchParams.get('name'));
  need(
    (u.origin === API && ((method === 'GET' && validGet && !u.search) || (method === 'POST' && validCreate))) ||
    (u.origin === UPLOAD && method === 'POST' && validUpload),
    'endpoint_not_allowlisted'
  );
  return u;
}

export function validateStorageRedirect(raw, from, hops) {
  const u = safeUrl(raw);
  const previous = safeUrl(from);
  need(hops >= 1 && hops <= 3, 'redirect_limit');
  need(previous.origin === API || STORAGE.has(previous.hostname), 'redirect_origin_invalid');
  need(STORAGE.has(u.hostname), 'redirect_host_not_allowlisted');
  return u;
}

export function validateBrowserUrl(raw, name) {
  const u = safeUrl(raw);
  need(u.origin === 'https://github.com' && !u.search &&
    u.pathname.startsWith('/' + REPOSITORY + '/releases/download/') &&
    u.pathname.endsWith('/' + name) && !u.pathname.includes('//'), 'browser_download_url_invalid');
  return u;
}

export function privacyStatus(status) {
  need(DENIALS.has(status), 'anonymous_access_not_proven_denied_status_' + status);
  return status;
}

export function decodeJson(bytes) {
  need(bytes.byteLength <= MAX_BODY, 'metadata_size_exceeded');
  let parsed;
  try { parsed = JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes)); }
  catch { throw new Error('metadata_json_invalid'); }
  need(object(parsed) || Array.isArray(parsed), 'metadata_shape_invalid');
  return parsed;
}

export function repositoryDiagnostics(value, expectedId) {
  const repo = object(value) ? value : {};
  const permissionsPresent = Object.hasOwn(repo, 'permissions');
  const permissionsObject = object(repo.permissions);
  const pushPresent = permissionsObject && Object.hasOwn(repo.permissions, 'push');
  let pushMetadata = 'ABSENT_UNKNOWN';
  if (permissionsPresent && !permissionsObject) pushMetadata = 'INVALID';
  else if (pushPresent) pushMetadata = repo.permissions.push === true ? 'PRESENT_TRUE' :
    repo.permissions.push === false ? 'EXPLICIT_FALSE' : 'INVALID';
  return {
    repository_object_present: object(value), full_name_matches: repo.full_name === REPOSITORY,
    repository_id_present: id(repo.id), repository_id_matches: repo.id === expectedId,
    owner_login_matches: repo.owner?.login === OWNER, public_visibility_matches: repo.private === false,
    default_branch_matches: repo.default_branch === 'main',
    permissions_field_present: permissionsPresent, permissions_object_present: permissionsObject,
    push_field_present: pushPresent, push_metadata: pushMetadata,
  };
}
export function assertRepositoryDiagnostics(d) {
  for (const key of ['repository_object_present', 'full_name_matches', 'repository_id_present',
    'repository_id_matches', 'owner_login_matches', 'public_visibility_matches', 'default_branch_matches'])
    need(d[key] === true, 'repository_check_failed_' + key);
  need(d.push_metadata !== 'EXPLICIT_FALSE', 'repository_push_explicit_false');
  need(d.push_metadata !== 'INVALID', 'repository_push_metadata_invalid');
  need(['PRESENT_TRUE', 'ABSENT_UNKNOWN'].includes(d.push_metadata), 'repository_push_state_invalid');
  return d; // UNKNOWN is not write proof. Only the later actual draft-creation201 can prove it.
}

export function validateRelease(value, expected) {
  need(object(value) && id(value.id), 'release_shape_invalid');
  need(value.draft === true && value.published_at === null, 'release_not_unpublished_draft');
  need(value.tag_name === expected.tag && value.target_commitish === expected.reviewed, 'release_identity_drift');
  need(value.name === expected.title, 'release_title_drift');
  need(value.url === API + PREFIX + '/releases/' + value.id, 'release_owner_drift');
  if (expected.id !== undefined) need(value.id === expected.id, 'release_id_drift');
  return value;
}

export function validateAsset(value, expected) {
  need(object(value) && id(value.id) && value.name === expected.name &&
    value.size === expected.bytes.length && value.state === 'uploaded', 'asset_shape_or_identity_invalid');
  need(value.url === API + PREFIX + '/releases/assets/' + value.id, 'asset_owner_drift');
  need(value.digest === 'sha256:' + sha(expected.bytes), 'asset_digest_drift');
  validateBrowserUrl(value.browser_download_url, expected.name);
  return value;
}

export function buildProof(report, context, expected, input, output) {
  const observed = name => report.observations.filter(row => row.check === name);
  const passed = name => observed(name).length === 1 && observed(name)[0].pass === true;
  const denied = name => observed(name).length === 1 && observed(name)[0].denied === true &&
    DENIALS.has(observed(name)[0].status);
  const draftRows = observed('draft_unpublished');
  const checks = {
    repository_identity_verified: passed('repository_identity_verified'),
    draft_unpublished: draftRows.length > 0 && draftRows.every(row => row.pass === true),
    input_authenticated_bytes_equal: passed(INPUT_NAME + '_authenticated_roundtrip'),
    output_authenticated_bytes_equal: passed(OUTPUT_NAME + '_authenticated_roundtrip'),
    anonymous_release_metadata_denied: denied('final_release_metadata'),
    input_anonymous_api_denied: denied('final_' + INPUT_NAME + '_asset_api'),
    input_anonymous_browser_denied: denied('final_' + INPUT_NAME + '_browser'),
    output_anonymous_api_denied: denied('final_' + OUTPUT_NAME + '_asset_api'),
    output_anonymous_browser_denied: denied('final_' + OUTPUT_NAME + '_browser'),
  };
  need(Object.values(checks).every(value => value === true), 'proof_observations_incomplete');
  need(passed('draft_creation_write_authorized') && observed('draft_creation_write_authorized')[0].status === 201,
    'proof_draft_write_not_proven');
  need(id(report.repositoryId) && id(expected.id) && id(input.id) && id(output.id), 'proof_identity_invalid');
  return {
    schema: 'northstar.private-media-canary.v1', repository: REPOSITORY,
    repository_id: report.repositoryId, draft_release_id: expected.id,
    canary_input_asset_id: input.id, canary_output_asset_id: output.id,
    source_workflow_path: '.github/workflows/private-media-canary.yml',
    source_sha: context.reviewed, workflow_run_id: Number(context.runId),
    workflow_run_attempt: Number(context.attempt), checks,
    canary_input: { name: INPUT_NAME, size: INPUT.length, sha256: sha(INPUT) },
    canary_output: { name: OUTPUT_NAME, size: OUTPUT.length, sha256: sha(OUTPUT) },
    status: 'CANARY_PRIVATE_ACCESS_VERIFIED', private_media_uploaded: false,
  };
}

async function boundedBytes(response, cap) {
  const declared = response.headers.get('content-length');
  if (declared !== null) need(/^[0-9]+$/.test(declared) && Number(declared) <= cap, 'response_length_exceeded');
  need(response.body !== null, 'response_body_absent');
  const reader = response.body.getReader();
  const pieces = [];
  let size = 0;
  try {
    while (true) {
      const row = await reader.read();
      if (row.done) break;
      size += row.value.byteLength;
      need(size <= cap, 'response_size_exceeded');
      pieces.push(Buffer.from(row.value));
    }
  } finally { await reader.cancel().catch(() => {}); }
  return Buffer.concat(pieces);
}

export async function runCanary(env, reviewed, { diagnosticOnly = false } = {}) {
  const context = validateContext(env, reviewed);
  const token = env.GITHUB_TOKEN;
  need(typeof token === 'string' && token.length >= 20, 'job_token_absent');
  const report = {
    schema: 'northstar.synthetic-private-media-canary.v1', status: 'RUNNING_NOT_PROVEN',
    providerProof: false, realMediaRead: false, releasePublishedByWorker: false,
    repository: REPOSITORY, reviewedSha: reviewed, runId: context.runId, attempt: context.attempt,
    releaseId: null, assetIds: [], observations: [], errors: [],
    write_authorization: 'UNKNOWN_NOT_PROVEN', repository_diagnostics: null,
  };
  const expected = {
    reviewed, tag: 'private-staging-canary-' + context.runId + '-' + context.attempt + '-' + randomUUID().slice(0, 8),
    title: 'DO NOT PUBLISH - synthetic media privacy canary',
  };
  report.stagingTag = expected.tag;
  const deadline = Date.now() + 8 * 60 * 1000;
  const record = () => writeFile('canary-report.json', JSON.stringify(report, null, 2) + '\n', { encoding: 'utf8', mode: 0o600 });
  async function request(url, { method = 'GET', body, authenticated = true, accept = 'application/vnd.github+json', storage = false } = {}) {
    need(Date.now() < deadline, 'finite_deadline_exceeded');
    if (!storage) validateApiUrl(url, method);
    const headers = { Accept: accept, 'User-Agent': 'NorthStar-synthetic-draft-canary', 'X-GitHub-Api-Version': '2026-03-10' };
    if (authenticated) {
      need(!storage && safeUrl(url).origin !== 'https://github.com', 'authorization_destination_refused');
      headers.Authorization = 'Bearer ' + token;
    }
    if (body !== undefined) headers['Content-Type'] = Buffer.isBuffer(body) ? 'application/octet-stream' : 'application/json';
    try {
      return await fetch(url, { method, headers, body, redirect: 'manual', signal: AbortSignal.timeout(Math.min(15000, deadline - Date.now())) });
    } catch { throw new Error('network_or_timeout_not_privacy_proof'); }
  }
  async function jsonRequest(url, options, expectedStatus = 200) {
    const response = await request(url, options);
    need(response.status === expectedStatus, 'authenticated_api_status_' + response.status);
    need((response.headers.get('content-type') || '').toLowerCase().includes('application/json'), 'metadata_content_type_invalid');
    return decodeJson(await boundedBytes(response, MAX_BODY));
  }
  async function currentDraft() {
    const value = validateRelease(await jsonRequest(API + PREFIX + '/releases/' + expected.id), expected);
    report.observations.push({ check: 'draft_unpublished', pass: true });
    return value;
  }
  async function assertAssociation(asset, spec) {
    await currentDraft();
    const list = await jsonRequest(API + PREFIX + '/releases/' + expected.id + '/assets');
    need(Array.isArray(list) && list.length <= 3, 'asset_list_shape_or_count');
    const matches = list.filter(x => x.id === asset.id);
    need(matches.length === 1, 'asset_not_in_same_draft');
    validateAsset(matches[0], spec);
  }
  async function binary(asset, spec) {
    await assertAssociation(asset, spec);
    let url = API + PREFIX + '/releases/assets/' + asset.id;
    let authenticated = true;
    for (let hops = 0; hops <= 3; hops++) {
      const response = await request(url, { authenticated, accept: 'application/octet-stream', storage: !authenticated });
      if (response.status === 200) {
        const bytes = await boundedBytes(response, spec.bytes.length);
        need(bytes.equals(spec.bytes), 'authenticated_binary_mismatch');
        return;
      }
      need(response.status === 302 && response.headers.has('location'), 'binary_fetch_status_' + response.status);
      const next = validateStorageRedirect(response.headers.get('location'), url, hops + 1);
      url = next.href;
      authenticated = false; // NEVER forward the API authorization to a signed storage URL.
      await response.body?.cancel();
    }
    throw new Error('redirect_limit');
  }
  async function anonymous(url, label, browser = false) {
    let response;
    if (browser) {
      validateBrowserUrl(url, label.includes(PROOF_NAME) ? PROOF_NAME : label.includes('output') ? OUTPUT_NAME : INPUT_NAME);
      try { response = await fetch(url, { headers: { 'User-Agent': 'NorthStar-synthetic-draft-canary' }, redirect: 'manual', signal: AbortSignal.timeout(15000) }); }
      catch { throw new Error('network_or_timeout_not_privacy_proof'); }
    } else response = await request(url, { authenticated: false, accept: 'application/octet-stream' });
    report.observations.push({ check: label, status: response.status, denied: DENIALS.has(response.status) });
    await response.body?.cancel();
    await record();
    privacyStatus(response.status); // A redirect or network failure is NOT affirmative denial.
  }
  async function privacyChecks(assets, phase) {
    await currentDraft();
    await anonymous(API + PREFIX + '/releases/' + expected.id, phase + '_release_metadata');
    for (const asset of assets) {
      await anonymous(API + PREFIX + '/releases/assets/' + asset.id, phase + '_' + asset.name + '_asset_api');
      await anonymous(asset.browser_download_url, phase + '_' + asset.name + '_browser', true);
    }
  }
  async function upload(spec) {
    await currentDraft();
    const url = UPLOAD + PREFIX + '/releases/' + expected.id + '/assets?name=' + spec.name;
    const value = await jsonRequest(url, { method: 'POST', body: spec.bytes }, 201);
    if (id(value?.id)) { report.assetIds.push(value.id); await record(); }
    const asset = validateAsset(value, spec);
    await binary(asset, spec);
    report.observations.push({ check: spec.name + '_authenticated_roundtrip', bytes: spec.bytes.length, sha256: sha(spec.bytes), pass: true });
    await record();
    return asset;
  }
  await record();
  try {
    const repository = await jsonRequest(API + '/repos/' + REPOSITORY);
    report.repository_diagnostics = repositoryDiagnostics(repository, context.repositoryId);
    await record();
    assertRepositoryDiagnostics(report.repository_diagnostics);
    report.repositoryId = repository.id;
    report.observations.push({ check: 'repository_identity_verified', pass: true });
    if (diagnosticOnly) {
      report.status = 'DIAGNOSTICS_ONLY_IDENTITY_VERIFIED_NO_MUTATION';
      return report;
    }
    report.status = 'ONE_DRAFT_SUBMISSION_PENDING_NOT_PROVEN';
    await record(); // Preserve tag even if a timeout makes the one POST outcome ambiguous.
    const created = await jsonRequest(API + PREFIX + '/releases', {
      method: 'POST', body: JSON.stringify({
        tag_name: expected.tag, target_commitish: reviewed, name: expected.title,
        body: 'SYNTHETIC CANARY ONLY. No real media. Keep unpublished. DO NOT PUBLISH.',
        draft: true, prerelease: true, make_latest: 'false', generate_release_notes: false,
      }),
    }, 201);
    if (id(created?.id)) { report.releaseId = created.id; expected.id = created.id; await record(); }
    validateRelease(created, expected);
    need(id(expected.id), 'created_release_id_absent');
    report.write_authorization = 'PROVEN_BY_DRAFT_CREATE_201';
    report.observations.push({ check: 'draft_creation_write_authorized', pass: true, status: 201 });
    await record();
    const input = await upload({ name: INPUT_NAME, bytes: INPUT });
    await privacyChecks([input], 'input');
    const output = await upload({ name: OUTPUT_NAME, bytes: OUTPUT });
    await privacyChecks([input, output], 'final');
    await currentDraft();
    need(report.observations.filter(x => x.denied === true).length === 8, 'privacy_check_count_mismatch');
    const proof = buildProof(report, context, expected, input, output);
    report.checks = proof.checks;
    const proofBytes = Buffer.from(JSON.stringify(proof, null, 2) + '\n', 'utf8');
    need(proofBytes.length <= MAX_BODY, 'proof_size_exceeded');
    const proofAsset = await upload({ name: PROOF_NAME, bytes: proofBytes }); // LAST asset upload.
    report.proof_asset_id = proofAsset.id;
    report.proof_sha256 = sha(proofBytes);
    await anonymous(API + PREFIX + '/releases/assets/' + proofAsset.id, 'proof_asset_api');
    await anonymous(proofAsset.browser_download_url, PROOF_NAME + '_browser', true);
    await currentDraft();
    report.status = 'CANARY_PRIVATE_ACCESS_VERIFIED';
    report.providerProof = true;
  } catch (error) {
    report.status = 'FAILED_OR_INCOMPLETE_PRIVACY_NOT_PROVEN';
    // Codes are our fixed strings; no provider bodies, URLs, headers or token values are retained.
    report.errors.push(error instanceof Error && /^[a-zA-Z0-9_:.-]+$/.test(error.message) ? error.message : 'unclassified_failure_redacted');
  } finally {
    await record();
  }
  return report;
}

export function summarizeReport(report) {
  return {
    status: report.status, providerProof: report.providerProof, repository: REPOSITORY,
    repository_id: report.repositoryId || null, draft_release_id: report.releaseId,
    staging_tag: report.stagingTag, canary_asset_ids: report.assetIds,
    proof_asset_id: report.proof_asset_id || null, proof_sha256: report.proof_sha256 || null,
    source_sha: report.reviewedSha, source_workflow_path: '.github/workflows/private-media-canary.yml',
    workflow_run_id: Number(report.runId), workflow_run_attempt: Number(report.attempt),
    private_media_uploaded: false, checks: report.checks || {}, errors: report.errors,
    repository_diagnostics: report.repository_diagnostics, write_authorization: report.write_authorization,
  };
}

export async function main(args = process.argv.slice(2), env = process.env) {
  if (args.length === 0) {
    console.log(JSON.stringify({ status: 'SOURCE_ONLY_CANARY_NOT_RUN', providerProof: false, realMediaRead: false }));
    return 0;
  }
  need(args.length === 3 && ['--execute', '--diagnose'].includes(args[0]) && args[1] === '--reviewed-sha', 'cli_arguments_invalid');
  const diagnosticOnly = args[0] === '--diagnose';
  const report = await runCanary(env, args[2], { diagnosticOnly });
  // This report contains only our codes, hashes, IDs and HTTP statuses. No response bodies/URLs.
  const result = summarizeReport(report);
  console.log(JSON.stringify(result));
  if (env.GITHUB_STEP_SUMMARY) await appendFile(env.GITHUB_STEP_SUMMARY, '\n## Synthetic draft canary\n\n' + JSON.stringify(result) + '\n');
  return report.providerProof || (diagnosticOnly && report.status === 'DIAGNOSTICS_ONLY_IDENTITY_VERIFIED_NO_MUTATION') ? 0 : 1;
}
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().then(code => { process.exitCode = code; }).catch(() => {
    console.log(JSON.stringify({ status: 'FAILED_CONTEXT_OR_SETUP_PRIVACY_NOT_PROVEN', providerProof: false }));
    process.exitCode = 1;
  });
}
