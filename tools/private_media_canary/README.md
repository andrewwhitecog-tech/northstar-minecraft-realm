# Synthetic draft-release privacy canary

Node20/22; built-in modules only. No media, local input path or arbitrary asset option exists.

Default: node canary.mjs reports SOURCE_ONLY_CANARY_NOT_RUN and makes no API call.
Source checks: node --test --test-concurrency=1 test_canary.mjs.
Execution is ONLY through reviewed trusted-main private-media-canary.yml in the exact owned public realm repository. No local admission bypass exists.

Root copies canary.mjs/test_canary.mjs/README.md to tools/private_media_canary and the supplied template to .github/workflows/private-media-canary.yml, independently reviews, merges, then manually dispatches the exact new main SHA. Source checks alone never establish runtime privacy; use the dated actual provider receipt for each dispatched revision.

The actual job validates context/actual repository, creates ONE uniquely named DRAFT targeted at that exact SHA, and uploads only fixed synthetic input/output text. It verifies exact authenticated bytes and affirmative anonymous401/404 on release metadata, asset-ID API and browser URLs. 403 (including rate-limit/abuse protection), redirects and network errors are inconclusive, not privacy proof. It never publishes/patches/deletes a release or creates Git refs.

CANARY_PROOF.json uploads LAST after the nine observed checks succeed, with schema northstar.private-media-canary.v1 and actual numeric repository/release/input/output/run identities, run attempt, source SHA/workflow path, and synthetic names/sizes/hashes. It has no self-ID. The job then verifies proof upload/readback/privacy and final draft persistence. Only a completed-success exact trusted run plus Root-pinned proof asset/hash can authorize a later consumer. A proof created before a later failure must not authorize media.

Full canary-report.json remains ephemeral in the job; small public logs/summary contain only IDs, hashes, statuses and fixed error codes. Signed URLs, tokens and provider bodies never enter output. Failed/ambiguous requests leave the staging tag and any known resource IDs for Root recovery; no blind retry/delete/overwrite is attempted. Keep every draft unpublished.

Only ordinary public-hosted runner compute and release assets are used. No cache/artifact upload or new API key. This is a test of access/privacy, not finished video or real-media permission.

Read-only --diagnose --reviewed-sha <SHA> uses the same trusted-context gates and only GETs repository metadata, emitting boolean identity/presence checks. Workflow operation defaults to diagnose; operation=canary explicitly permits the subsequent synthetic-only operation. Missing permissions.push is ABSENT_UNKNOWN, not write proof; explicit false or malformed metadata rejects. Every actual canary must prove write by its one validated201 draft creation before it can emit proof.
