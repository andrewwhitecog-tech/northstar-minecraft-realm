# Exact-source vanilla trim smoke

This source-only payload contains no world, player data, secrets, local paths or original private plan. It executes only on an explicitly selected GitHub-hosted Linux runner. Default command validates payload only; native execution additionally requires --ci --execute and the reviewed PAYLOAD.json SHA256.

The driver implements sixteen concrete public cases: six authentic call sites, one integer-as-string differential control, and nine malformed or unknown-item refusal cases. It compares actual original-versus-guarded barrel, operative storage, result/success presence and parent continuation. Native parser/instantiation refusal is recorded separately from guard rejection; unknown evidence fails closed. Forty other cases and all twenty-four macro holds remain unresolved. Implementation and source tests alone do not establish native acceptance. Optional six-location RCON timings/debug profiling are evidence, not automatic performance acceptance; this workflow does not request those timings.

Mojang server/libraries are NOT vendored: transport.json binds the official outer URL/hash and all40inner/server+librarymembers to the original local native dependency pins. Runtime fetch verifies outerSHA1/SHA256/size and every extracted member SHA256. A fresh superflat proof world is generated. Nothing attaches to an existing server.

Commands: python test_source.py; python ci_runner.py (validation only). Root owns hosted workflow/run and review. No artifact/cache upload is part of this payload. Do not publish runtime server.properties or world files.
