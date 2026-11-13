# Original pirate fauna source build

This packet contains original cuboid geometry, palette textures, articulated rigs, animation export recipes, a software preview renderer, and actual-file validation. It contains no copied game textures or models.

The first exporter covers six assets: skeletal parrot, owl and fish; living and skeletal sharks; and a jeweled living dolphin. The expansion exporter covers twelve distinct additions: clam, oyster, rat, mouse, two neon rodents, two crowned rodents, a huge mutant rabbit boss, and three original Victorian rabbit enemies. The expansion does not export the first six again.

Copy the allowlisted files to `tools/pirate_fauna/`; copy `workflow_template.yml` to `.github/workflows/original-pirate-fauna-assets.yml`. Pull requests run genuine source tests only. An owner dispatch on public main, bound to the exact reviewed source_commit SHA, runs on GitHub-hosted Ubuntu 24.04 with Python 3.12 and the hash-locked Pillow 12.3.0 wheel. No local fallback, paid provider, Git/API write, world installation or automatic entity spawning is included.

The workflow runs actual source tests, exports the six assets first into `generated_base_v01/`, validates those bytes, exports the twelve additions into `generated_expansion_v02/`, and validates the combined output. Failures retain real traceback and command logs. A 32 MiB artifact ceiling and one-day retention bound the upload.

Actual-file checks cover model identity, bone topology, rigid-node GLB animation, finite positions/quaternions, animated bounds, Java bone poses and element limits, Bedrock bone/animation correspondence, decoded preview sheets, and distinct articulated GIF frames. They do not establish visual quality, native game rendering, collision, AI, crossplay mapping, spawn safety or player experience.

The recipes produce explicit opt-in assembly source, not a working installed mob system. No numeric registry IDs are allocated. Private fauna behavior, water/air needs, bounds, population limits and adoption remain separate owning-system work. Hostile encounter behavior is not part of these asset files.

The generated software previews require personal visual review before acceptance. A successful hosted run is export evidence only.
