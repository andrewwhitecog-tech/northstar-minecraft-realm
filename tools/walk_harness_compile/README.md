# Public hosted compile payload: held-mining route harness

This payload contains original harness sources and authentic mod resources only. It does not contain Minecraft/Fabric dependency binaries, worlds, player data, credentials, route recordings or workstation paths. Compilation and native behavior are not yet verified.

Run node cloud-compile.mjs for offline validation only. It checks the allowlisted text files, source/resource digests, pinned logical classpath and mod-resource contract. It performs no download, JVM launch, packaging or installation.

The exact legacy compiler classpath has 132 ordered entries / 126 unique artifacts (six duplicate entries retained): 74 libraries from Mojang's official 26.3 metadata, 44 Fabric API modules, seven ASM/Fabric Loader/Mixin artifacts, and the Minecraft client. Windows native JAR entries remain logical compile inputs for source parity; javac never loads or executes those native libraries. Official dependency downloads total 136394910 bytes. No local dependency JAR is copied.

The official version manifest resolved Minecraft26.3 metadata SHA-1 9f67e10ed013deeaad20ac3c800652765d493408. That remote metadata body hash matched, and its client download pin matched the inspected installed version. All 74 client-library HEAD sizes and all 51 Maven published SHA-1/HEAD availability checks succeeded during preparation; individual URLs/pins/timestamps are in classpath-manifest.json. SHA-1 is the publisher's integrity pin, not an independent publisher-signature claim. Hosted downloads verify published size and SHA-1 before compilation.

## Root-owned GitHub workflow integration

Use a standard GitHub-hosted Ubuntu runner in the specified public repository, with Node and JDK25. Root owns the workflow and draft PR; this package does not publish or start a job. Set these explicit workflow environment declarations:

- NSP_ALLOW_PUBLIC_CLOUD_JAVAC=1
- NSP_PUBLIC_REPOSITORY=true (set from the actual public-repository context, never for a private repository)

Then invoke node <payload-directory>/cloud-compile.mjs --compile. The driver additionally requires CI=true, GITHUB_ACTIONS=true, RUNNER_ENVIRONMENT=github-hosted, RUNNER_OS=Linux, the exact declared repository, a normal hosted-runner checkout/temp location and its payload inside that checkout. Windows, WSL, self-hosted runners and ordinary local invocation are refused before downloads or JVM launch. These are operational guardrails, not cryptographic host attestation. Never spoof them to bypass local governance.

Compilation uses the pinned official downloads, release25, annotation processing disabled, one active processor, SerialGC and a 384 MB maximum heap. Only the original namespace classes and the two reviewed resources are packaged. There is no game launch, ffmpeg run, Minecraft dependency shading, world write, server test or installation. The original recording implementation remains source only until a separately authorized native runtime actually invokes it.

The candidate filename includes the v02 source revision and source digest. Authentic fabric.mod.json retains version2.0.0 and mod ID nsp_route_walk; the unique candidate filename distinguishes this build without changing retained resource bytes. Do not install it alongside another JAR with that mod ID. Owner review precedes any replacement.

## Free job-log delivery

No upload-artifact or cache action is used. After an actual successful build, the driver checks the own-code JAR listing and a maximum size of 1000000 bytes. It prints one NSP_JAR_METADATA JSON line (filename, actual SHA-256, size and compile-only status), then bounded base64 lines between NSP_JAR_BASE64_BEGIN and NSP_JAR_BASE64_END. Root retrieves those job logs, joins only the marked base64 body, decodes the candidate, verifies its byte count and SHA-256, and saves it to canonical project/download homes. Dependency JARs never enter that output. A reconstructed JAR is a compiled candidate; native survival-break behavior remains unverified.

Never commit build/ or dependency binaries. The local source-check receipt is metadata/source verification only. A public download or compile result does not establish a native protection pass.
