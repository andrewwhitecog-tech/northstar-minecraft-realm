# Private Minecraft promo source QC and conform

Runnable SOURCE ONLY. No private input, token, canary evidence, media output, or actual cloud run is included. The default command validates payload identity without network or FFmpeg. Source tests use synthetic HTTP responses and small synthetic ZIPs; they do not establish GitHub privacy or native media acceptance.

## Root-owned promotion and dispatch

Copy these reviewed sources to tools/private_media_conform in the public repository; install workflow.template.yml as .github/workflows/private-media-conform.yml. Do not publish source media or private config files. Only the fixed basenames, numerical asset identities, byte sizes, digests, actor policy, and review facts belong in media-config.json. All numerical IDs default to null and block execution. Use the existing same unpublished draft from the harmless canary. Never publish that draft.

Fill repository_id from the actual repository API; draft_release_id, draft_tag and draft_target from that same actual draft. draft_target must equal the separately reviewed canary source SHA. Fill canary.run_id, run_attempt, source_sha, proof_asset_id and proof_sha256 from the actual completed-success canary; proof_size is optional, bounded to64KiB. The worker independently verifies the repository, API run identity/actor/path/attempt/conclusion, Root-pinned proof bytes, all nine proof checks and authenticated harmless canary bytes. It rechecks anonymous release metadata and both anonymous asset routes. ONLY401/404 count as denied;403 is inconclusive and blocks. No private source download occurs before these gates succeed. Canary source SHA may differ from the later reviewed media-job SHA.

The only input roles and basenames are:

| Role | Exact basename |
|---|---|
| base | P4_RING_OPENS_9x16_v14R_YT_SFX_PICTURE_NOCARD.mp4 |
| c6 | C6_best.mp4 |
| p1 | P1_WAKE_9x16_v07.mp4 |
| p2 | P2_SOMETHING_WOKE_9x16_v08.mp4 |
| p3 | P3_THE_COST_9x16_v13.mp4 |

Root supplies each same-draft asset_id, exact size and SHA256 after the real canary and private-source review. The worker checks asset membership, uploaded state, metadata and downloaded bytes. Each input is capped at512MiB and total input at1GiB. Output ZIP is capped at512MiB. Root owns lawful source authorization and uploading inputs; this payload does not upload them.

## Two manual phases

First dispatch source-qc at the exact Root-reviewed main SHA, passing that SHA as reviewed_sha. Execution requires genuine GitHub-hosted Ubuntu24.04, manual main workflow context, exact public repository and configured trusted actor, plus the actual in-progress API run identity. Local Windows/Linux/WSL or self-hosted execution is rejected. No local governor bypass is provided. Default command is:

    nice -n 19 uv run --no-project --python 3.12 python -B cloud_worker.py

The source-QC phase downloads the five pinned inputs and produces a private ZIP containing actual probes, five C6 window images, full-base timeline and boundary images,4fps grayscale motion/reuse estimates against P1/P2/P3, EBU R128 stderr summaries, waveform and packet-verified extracted original audio. Source window is frames83 through146 at30fps (64frames;2.766667–4.9seconds). Both QC frame/motion extraction and conform invoke the same canonical fps=30 → trim start_frame83/end_frame147 → setpts chain before cropping; source QC uses no input seeking. Replacement is base frames878 through941. The existing retained EDL source intervals are recorded as source-study context, not proof of visual quality. Motion/reuse thresholds only report technical eligibility, never creative approval. Image/audio files and tool stderr remain inside the draft ZIP.

Download the ZIP privately, verify the reported hash and personally review the actual source frames, motion/reuse results and audio. For conform, fill source_qc with the exact first output ZIP asset/size/SHA and successful run/attempt/source SHA. Fill approval with decision APPROVE_SOURCE_FOR_ISOLATED_CONFORM, allowed reviewer, UTC, exact ZIP asset/SHA/run, input_manifest_sha256 from its receipt, both personal-review booleans and the exact frame intervals. The worker verifies this binding, the prior successful Actions run and SOURCE_QC.json inside the pinned ZIP before downloading source media. A failed source-QC receipt cannot authorize conform. Changes to input pins invalidate approval.

Dispatch conform separately at its newly reviewed main SHA. It uses the NOCARD base; inserts only the64frame native C6 window; retains all other base timing and copies the complete original audio packet stream. No still animation, added text, synthetic camera motion, new scene generation, or new claims. The private output ZIP contains the actual40second/1200frame candidate, representative five timeline images plus old floor/card-boundary images, probe, full A/V decode receipt, actual audio/waveform/loudness and4fps reuse estimate. Exact copied-audio packet equality is required. Reuse outside the limit is reported NOT_FOR_RELEASE. No automatic creative PASS exists; every output requires Root personal visual and auditory QC.

## Privacy and output persistence

GITHUB_TOKEN exists only in the job's worker environment and memory; it is popped before media execution and never inherited by FFmpeg. Manual downloads permit only exact GitHub API routes and an explicit HTTPS release-CDN hostname allowlist. Authorization/cookies are never forwarded to signed CDN redirects. Redirect targets, private media, audio and tool stderr never enter public logs. Failures expose fixed reason codes only. Every asset read and output upload is surrounded by same-draft/unpublished checks. Output names are unique per phase/run/attempt; existing names block, never overwrite. No release publication/edit/delete, artifact upload, cache, external provider or paid generation is implemented.

An output is promo-v16-source-qc-RUN-ATTEMPT.zip or promo-v16-conform-RUN-ATTEMPT.zip in the SAME draft. Actual upload readback checks exact bytes, then requires anonymous API and browser access to the NEW output asset to return401/404;403 blocks success as inconclusive. Stdout contains only small asset ID/size/SHA/run/source/release/status metadata. A technical failure can still upload a private diagnostic ZIP, then returns nonzero. Root auto-downloads the output to canonical project homes after successful execution and reviews it; the pipeline does not open playback invisibly.

## Source validation

    nice -n 19 uv run --no-project --python 3.12 python -B -m unittest discover -s tests -v

Tests are stdlib-only and launch no FFmpeg, JVM, network or renderer. Read SOURCE_TEST_RECEIPT.json for the actual last local source-only test run. Hosted FFmpeg syntax, actual API permissions/privacy, upload persistence, final pixels and actual audio remain unrun until Root's real dispatch and review. Standard hosted compute/release-asset cost assumptions belong to Root's feasibility review; no third-party fee is initiated here.
