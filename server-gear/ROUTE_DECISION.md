# Backpack and accessory route — 2026-10-30

Choose our Fabric 1.21.1 mod with sgui 1.6.1+1.21.1 now. The prototype uses only vanilla item IDs and vanilla chest screen types. No custom client networking, item registry or client mod is required by its code. Actual Java protocol tests and Geyser acceptance are separate.

Primary evidence retrieved this run:
- https://github.com/Patbox/sgui/tree/1.6.1%2B1.21.1 — pinned source inspected (SimpleGui, SlotGuiInterface, VirtualScreenHandler).
- https://api.modrinth.com/v2/project/trinkets-polymer — server_only; includes 1.21.1. Versions endpoint returns 3.10.0+polymerport.2 for 1.21.1. This route is available now; it is not inherently blocked until the upgrade.
- https://api.modrinth.com/v2/project/nets — mostly slot data packaged as a mod; 1.21.1 release 0.3.6. Its purpose is more slots than two rings, while our request is exactly 2 rings/1 amulet/1 charm. NETS is unnecessary for these exact counts.
- https://github.com/Patbox/polymer — foundation for future NorthStar registered content. Current prototype doesn't require Polymer because vanilla component-bearing items suffice.

Our route controls holder locking, nesting and persistence in a single transaction path and gives every player the same 2/1/1 pouch. Reconsider Trinkets after the server version is picked and its complete stack passes Geyser. Do not claim that either route has passed Geyser from server-only metadata.

## Storage and survival
Each backpack is max-stack 1 with a vanilla container component. Mutation copies the entire small inventory into that component immediately. No external UUID contents database. Pouch has 4 typed slots, one active pouch per player. Storage objects and any container/bundle are rejected in storage. Holder slot, number swaps, double-click collection and creative cloning are locked while open. Drop-selected packet is blocked while a storage screen is open. Ordinary closed-item transfer/hopper/drop/death/relog uses vanilla persistence.

Crafting is at a nearby smithing table with an anvil and heat within 2 blocks. /ringwright exposes band → gem-setting → alchemical enchant. Upgrade the held backpack there; components and UUID stay on the same item. No consumptive upgrade occurs when insufficient materials. Nonleather tiers require the exact nsp_material tags bison_hide, elk_leather, moose_hide, beaver_pelt; those wildlife sources are not built by this prototype. No fake fauna claims.

Rings use level-I vanilla effects, different effects coexist and duplicates do not amplify. Ember Ward begins only after 3 seconds of lava exposure, Hearth heals half a heart every 10 seconds after at least 5 seconds still at full food. Lodestone pulls normal item entities within a sphere of 6 blocks without bypassing pickup ownership. Lantern creates level-11 vanilla light in air only, cleanup journal written before world mutation; cleans on movement, disconnect, shutdown, next startup. Spectral charm outlines nearby mobs to all viewers (vanilla glowing is not per-viewer). Slowfall amulet and spectral charm are costly endgame recipes.

## Explicit gaps
All gear uses the noningredient vanilla recovery compass carrier; native recipe ingredients are scanned in the runtime self-test. Knowledge books were inspected and rejected because their use method consumes one even without recipes. No original VORATH meshes/CMDs are substituted for the models owned by Antigravity; vanilla item appearance only. No worn backpack render. Bench's styled Alchemy-quarter architecture is not built here. Functional bench is a real smithing/anvil/heat arrangement on a world copy. Automatic ordinary smithing UI recipes are not present; /ringwright is the transactional crafting interface at the bench. Real Geyser/Xbox menu and all edge-case client tests are required before acceptance. No Bloom access/writes/restart.

Night Eye refreshes 260 ticks of night vision to avoid vanilla fade/blink. It may linger for up to 13 seconds after unequipping; unrelated potion effects are not removed. Other potion rings refresh 45 ticks.

The CI Geyser fixture binds only loopback and explicitly disables Bedrock login validation for its offline packet client. It uses no Microsoft/Xbox account, no cached tokens and no existing server config. This verifies protocol inventory behavior; authenticated console joining and Xbox visual acceptance remain separate.
