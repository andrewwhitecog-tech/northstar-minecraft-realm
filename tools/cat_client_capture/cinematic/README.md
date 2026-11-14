# Portable cinematic admission source

This is a complete source-only Fabric client module for Minecraft26.3/Java25. It does not start Minecraft, launch a recorder, install a profile, or qualify native footage. Root owns runtime integration and pixel review. Optional Iris/Sodium observers and private world/profile data are excluded.

## Explicit modes

The default three-argument CinematicProgram constructor retains OFFLINE_NATIVE_CINEMATIC and rejects translation below0.01blocks. OFFLINE_NATIVE_ANIMATED_SUBJECT explicitly permits an exactly fixed XYZ/yaw/pitch camera; its endpoints must match exactly. That permission proves neither animated subjects, advancing world ticks, shader health nor real-time gameplay FPS. Those require actual runtime state, observed changing frames and personal visual review. Encoded fps describes the authored output timeline only.

RouteWalk accepts a cinematic step with cinematic (relative take name), mode (one exact supported label), poses (two concatenated5-component feetXYZ/yaw/pitch poses), frames2..600 and fps1..60. It retains the existing real-time recorder/camera branch separately. The HEAD mixin sets the pending authored pose; TAIL captures one actual1280x720 RGBA framebuffer. Reserved RAM is retained until actual raw+index flush. The camera advances only after commitment; no duplicate padding, interpolation or still-image camera trick is introduced.

## Deferral contract

CinematicFrameState.deferRender(ticket,now) accepts only the exact current RENDER ticket before GPU submission. It returns READY without advancing the committed index. The next ticket requires a strictly larger render ID. Old tickets fail closed; GPU/WRITE/READY deferrals fail. Pending/overall deadlines are checked before deferral; the global start and budget never reset. It is a state API, not a readiness bypass: an external renderer observer must establish actual current readiness before admission/submission. No synthetic zero queues or compatibility fallback is provided here.

## Portable paths and source completeness

All nine production classes compile from this directory; no private baseline JAR or precompiled payload is read. Fabric metadata owns only nsp.walk.mixin, leaving the entrypoint/helper package separate. The official client JAR is a byte-pinned build dependency downloaded during hosted compilation; it is not committed or bundled in the output JAR.

The old workstation-specific real-time spool allowlist is replaced by an explicit existing task directory below nsp.walk.dir/realtime_spool/<run>. It must be exactly one child, regular/resolved without a linked ancestor; spool files use CREATE_NEW. The caller prepares that private run directory. The wall-clock sampler, loss counters, queue/drain behavior and existing real-time acceptance semantics are otherwise unchanged. Cinematic destinations use fresh per-take directories below nsp.walk.dir/cinematic_spool/<name>. No local path, world, account or credential is required.

## Source-only commands

Hosted public pull-request source compilation (the builder rejects local execution):

    python3 -B tools/cat_client_capture/cinematic/portable_build.py --execute --expected-commit "$GITHUB_SHA" --output "$RUNNER_TEMP/cinematic-source"

Source-pin check without downloads/processes:

    python3 -B tools/cat_client_capture/cinematic/portable_build.py

Standalone stdlib regression command for Root/admitted execution:

    python3 -B -m unittest discover -s tools/cat_client_capture/cinematic -p test_spool_verify_mode.py -v

The independent workflow job compiles all9 production classes and all6 JUnit classes using the official locked dependencies, then requires actual XML totals39tests/0failures/0errors/0skips and actual stdlib totals4tests/0failures/0errors/0skips/0expectedFailures/0unexpectedSuccesses. It retains raw logs, counts and an own-classes-only candidate JAR. Missing/empty/partial reports fail. Neither compilation nor tests have been run for this new portable port. The retained upstream build recorded39clean JUnit cases; that historical result is not this port's result.

Two Fabric API module dependencies are added using exact retained byte sizes/SHA256 and their official Fabric Maven coordinates. Their portable URL fetches remain unexecuted until Root/CI runs the builder. No extra installation or fee is required by this source.

## Remaining native requirements

Initial/dynamic/postcapture renderer readiness, current world/chunk and pose evidence, animation/tick measurements, strict spool CRC/IDs, normal owned-process closure, decode/PTS checks and personal image/audio QC remain the capture controller's responsibility. No native controller, native acceptance, gameplay proof or finished promo is supplied or implied. Existing capture workflow jobs and guards are preserved.
