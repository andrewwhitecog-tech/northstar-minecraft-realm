# Exact-source vanilla trim smoke

This source-only payload contains no world, player data, secrets, local paths or original private plan. It executes only on an explicitly selected GitHub-hosted Linux runner. Default command validates payload only; native execution additionally requires --ci --execute and the reviewed PAYLOAD.json SHA256.

The proof executes two cases with real vanilla command entries: original-versus-guarded barrel effects and unknown-item guard early return/parent-frame continuation. The remaining54cases and all24macroholds remain unresolved. Optional six-location RCON timings/debug profiler are evidence, not automatic performance acceptance.

Mojang server/libraries are NOT vendored: transport.json binds the official outer URL/hash and all40inner/server+librarymembers to the original local native dependency pins. Runtime fetch verifies outerSHA1/SHA256/size and every extracted member SHA256. A fresh superflat proof world is generated. Nothing attaches to an existing server.

Commands: python test_source.py; python ci_runner.py (validation only). Root owns hosted workflow/run and review. No artifact/cache upload is part of this payload. Do not publish runtime server.properties or world files.
