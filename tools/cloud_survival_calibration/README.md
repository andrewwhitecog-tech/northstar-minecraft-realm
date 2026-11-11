# Reviewed public cloud survival calibration — SOURCE ONLY

This is runnable candidate source for Root’s privacy/source review. Native Minecraft client/server/Xvfb execution is NOT_RUN. No local Java, server, renderer, paid provider, cache, cloud workflow, private world or shared profile was used. The actual compiled owned harness is included, not rebuilt.

## Run model

Promote only PAYLOAD.json and its exact listed files to tools/cloud_survival_calibration in the existing PUBLIC northstar-minecraft-realm repository. After Root independently reviews the source/pins/privacy, it may promote workflow.template.yml to .github/workflows and manually dispatch with SHA256(PAYLOAD.json). The manual job additionally requires the main branch and repository-owner actor andrewwhitecog-tech. There is no PR/push automatic trigger, no deployment/write permission, no secret input, and no cache/artifact-upload action. No workflow was launched by this contributor.

Default command native_calibration.py validates source pins only. --execute additionally requires the exact reviewed payload hash and explicit GitHub-hosted Linux/public-owned-repo environment. Windows/local execution, WSL indicators and Microsoft kernels are refused before any runtime download or native launch. Payload entries, the manifest, the lock and the owned JAR reject unresolved file/parent symlinks and Windows junctions before path resolution. See FEASIBILITY.md for boundaries.

## Actual implementation

- Official26.3 client/server metadata and asset index; FabricLoader0.20.1 profiles; FabricAPI0.165.0+26.3 and Flan26.3-1.12.8.b public Modrinth hashes. Download paths/origins/bytes/hashes are bounded and verified. No user libraries/profile/config/world are uploaded. Public copyrighted runtime/assets download only into ephemeral hosted runtime, never into this source payload or artifacts.
- Own nsp-route-walk-heldproof-v02.jar: SHA b19fefcfee9980099dbf3ebd8426fe8da1f13346c37c347723b6ebc4cc99b532,16685bytes. Only own four Java classes and two Fabric resources; FabricAPI is a separately pinned official download. Same modID must never be installed beside another route harness.
- A fresh loopback-only Fabric/Flan server with one new admin claim; fresh local-client profile and servers.dat; random offline name/derived UUID and separate random claimUUID. RCON password generated in hosted memory/config and never printed. Empty ops.json and no trust/permission provider. No access to Bloom/master/private land or players.
- Actual Fabric KnotClient under owned Xvfb display and Mesa llvmpipe,800×450,FPS20. It is the real Minecraft renderer/client, not Mineflayer, a packet bot or a framebuffer substitute. Linux launch arguments derive from the actual pinned26.3/Fabric profiles; the retained Windows token-forwarder simply calls KnotClient, so it and the Windows hidden-window agent are not copied. Access token0 is only a fresh offline loopback-fixture credential, not a real account token.
- Same continuous living non-op survival player, the same uniquely tagged wooden pickaxe, and bone_block[axis=y] in all3 legs: permittedA -> claimedB -> permittedC. Targets and all stone/air geometry are placed BEFORE the measured mining sequence. The tool is installed once; only the selected slot changes afterward. No target restoration or writes occur during the measured legs.
- Preflight requires both actual client row and server position to agree within0.25m, stable measured stand, solid floor/clear feet/head, server-anchored eye probe and actual block-interaction-range attribute, plus an unobstructed voxel ray. The judge waits for genuinely loaded fixture chunks before building.
- Each main dig gets240clientticks,8×the retained LSL expectation of30 for bone/wood; actual outside controls must still prove it works. Each requires DIGSTART and exact-target DIGHOLD with client-predicted air. No missing positive control can become a protection pass.
- After the judged mark, wait at least6wallseconds AND120advancing server ticks while checking exact expected block state. save-all flush, then independently decode the real generated MCA file. The claim leg’s post-ACK3tick probe must show the real client has resynced to bone; then flush/read again. Final clean shutdown repeats all3 persisted states plus saved player survival/tool-identity/damage2 checks.
- FatalERROR/STUCK/AWAIT_TIMEOUT aborts; no later leg runs. The pinned harness’s fatal-await/dighold-finally properties are retained. The judge acknowledges only after authoritative checks/save evidence, never as a passing result in itself. Cleanup closes only exact owned client/server/Xvfb process handles; no foreign taskkill, lease manipulation or OS controls.

## Results and real limits

Latest checks/revision_02_guards/source_tests.actual.*: actual uv/unittest execution,19run,18passed,1skipped,0failures/errors; exit0,1.114s test time. The actual Windows parent-junction rejection, WSL/Microsoft-kernel gates and exact official JVM native-path contract passed. The file-symlink case is explicitly skipped because this Windows token lacks symlink creation privilege; it runs on hosted Linux. Earlier14/14 receipts and pre-change sources remain preserved under checks/. These are source/parser/metadata checks, including synthetic NBT-region fixture decoding; NOT real mining results or a fake game model. Root must inspect the source and then obtain actual hosted evidence. No shared harness adoption/hold clearance follows from them.

Unknown native response, absent tool/position/mark, no client prediction, failed positive control, missing persisted file, unsupported actual NBT/compression, renderer/client boot failure or cleanup failure makes the native run FAILED/INCONCLUSIVE. Nothing is defaulted to a native pass. Exact fresh-world server/client logs, commands, real rows, saved states and optional real fixture PNGs are emitted through job logs; no paid artifact/cache storage is requested. Root must decode/inspect PNGs before claiming visual proof.

Adoption stays with the director/Root after a genuine3-leg pass and independent review. This bundle does not install or mutate any canonical harness, server, world or account.

## First actual hosted attempt and graphics recovery

Run43044823507 downloaded the official runtime and booted the real Fabric/Flan server, but the client could not create a GLX visual and its Vulkan fallback also failed; no client joined and no mining leg passed. Server shut down cleanly, exit0. The recovery installs official Ubuntu Mesa/GLX diagnostics, requires an actual llvmpipe OpenGL preflight, chooses SDL X11 explicitly, fixes the rejected client simulation-distance value and fails early if both graphics backends fail. Native judge/expectations are unchanged; the next actual run must establish compatibility and mining behavior.

## No-APT recovery revision

The attempted Ubuntu package recovery failed DNS resolution before native execution. This revision uses a real ctypes GLX context probe against the libraries already installed, capturing actual renderer strings and a completed clear/error check. It removes APT, preserves SDL X11/software settings, and leaves every mining/persistence judge unchanged. A successful legacy context is only a preflight; actual Minecraft rendering, joining and all three survival legs remain mandatory and unproven before the next run.
