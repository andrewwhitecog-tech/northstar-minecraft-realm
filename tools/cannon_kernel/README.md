# Cannon kernel: offline source/build fallback

This directory contains a generic, relocatable cannon datapack generator and a synthetic fixture configuration. It contains no existing world save, player identity, live-server configuration or fishing-retreat content. Any companion native component probe has its own source packet and explicit hosted execution guard.

The generator/config bytes originate from the frozen source hashes recorded in PUBLIC_SOURCE.json. The portable tests retain ConfigTests and GeneratedPackTests plus their real unittest XML/JSON reporter. Three platform-specific local-wrapper path tests were omitted; the remaining source contains 28 test methods. That count is a source inventory, not a test result.

## Intended execution after coordination

Do not duplicate a pending local batch. The workflow is prepared for pull requests touching only this contribution or its own workflow path, and manual dispatch. Root must reconcile the pending local attempt before creating a PR or dispatching. Nothing runs merely by reading these files.

For an authorized hosted/offline run with a fresh output directory outside this source folder:

    python3 -B tools/cannon_kernel/run_source_checks.py --execute --output /NEW/OWNED/OUTPUT

Without --execute the helper describes its plan and does not build/test. With it, source hashes are checked, the actual generator runs, generated file hashes are verified, and the actual unittest suite emits JSON/XML and full stdout/stderr. A cannon-pack.zip is produced only after the checks pass. Failure evidence is retained; no result is hardcoded. No pip install, game/server/client runtime, GPU, native graphics or network access is used by these Python steps.

The explicit demo/build Minecraft function is generated source; this workflow never executes it. It would place a local fixture only when separately invoked in an authorized fresh native copy. It is not an installation/adoption path for an occupied world. Markers model shots; native collision, controls, ammunition transactions, target behavior and cross-play remain unproved until genuine game checks.

## Workflow scope

.github/workflows/cannon-kernel-source.yml uses ubuntu-24.04, a25minute cap, contents:read only, credential persistence disabled, and official checkout/upload actions pinned to exact commits. It has no push trigger, pull_request_target, secrets, cloud calibration invocation or changes to existing native/main-only guards. No additional paid runner, billing setting or account configuration is requested.

A small artifact can retain the generated pack and actual test evidence for1day. The helper withholds upload if the measured output plus receipt allowance exceeds2MiB; it does not erase logs to fit. GitHub documents standard hosted runner execution in public repositories as free, subject to service limits; this is not a guarantee that any account restriction or artifact quota is absent.

Official references:
- https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax
- https://docs.github.com/en/actions/concepts/billing-and-usage
- https://docs.github.com/en/actions/tutorials/store-and-share-data

## Validation boundaries

The source workflow builds the datapack and executes the portable unittest suite. Its receipt records the actual result for that exact source revision. A passing source run reports nativeVerified=false and liveInstalled=false. Native component checks are separate and do not accept the full pirate encounter, moving ship, client presentation, world integration or public release.

Hit-time target functions recheck the configured dimension and current site bounds, in addition to registration-time type and ownership checks. Previously registered targets that leave the area must not take damage from an in-area shot.
