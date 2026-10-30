# NorthStar backpacks and rings — server-side prototype

This module adds item-backed backpacks, an accessory pouch and a survival Ringwright workshop to Fabric 1.21.1. It is a separate Lane 4 module; it does not load the old whole-world Realm mod.

Use a backpack or type /backpack. Tiers contain 9, 18, 27 or 54 slots. Use the accessory pouch or type /accessories: the first two slots accept rings, the third an amulet and the fourth a charm. Only the first pouch in inventory applies effects. A backpack or other container cannot go inside either storage item. While open, the backing item cannot move or be dropped. Its contents are saved directly on the item as you move them.

Build a smithing table with an anvil and a lit campfire, fire or lava within two blocks. Stand within four blocks and use /ringwright. Make a metal band, hold it while setting a gem, then hold the setting while alchemically enchanting it. The menu lists costs. Enchanting costs 8 lapis, 4 redstone and 3 experience levels. A failed payment takes nothing. Duplicate rings do not increase effect strength.

The first set: Night Eye, Strider, Miner's Band, Tidebreath, Ember Ward (after 3 seconds in lava), Lodestone (6 block item attraction), Lantern Ring (moving level-11 light), Hearth (half-heart every 10 seconds after resting at full food), Luck of the Fold. Slowfall amulet and spectral charm are endgame extras. Spectral glow is visible to everyone nearby.

Craft a leather backpack at the workshop with 8 leather, 2 string and a chest. Upgrade the held backpack there. Higher tiers require exact custom-tagged bison hide, elk leather, moose hide and beaver pelt. Those fauna loot sources are a separate pending job: higher tiers can be tested on the copy but are not yet earnable through those absent animals. The pouch costs 4 leather, 2 string and 1 amethyst.

The prototype uses recovery-compass item icons and original names. Original VORATH backpack/ring meshes, worn-back rendering and the finished Alchemy-quarter bench architecture are not included. Functional use is through vanilla chest menus. Ordinary smithing-table recipe screens are not integrated yet; the workshop menu performs the upgrade at the real table.

## Copy-only validation

No Bloom writes, restarts or account changes. The finite fixture binds Java26224, RCON26225, ViaProxy26226 and BedrockUDP19224 to loopback. It copies a retained offline test world's level and one region. It launches its own processes, runs tests, saves and stops them.

The deliverable's verification status is in CURRENT.md. A successful build or headless Bedrock packet test does not establish Xbox visual acceptance. Full Java/Xbox hands-on play and original art remain acceptance checks.

## Source/build

Java21, Gradle8.8 wrapper, Fabric Loader0.16.5, Fabric API0.105.0+1.21.1 and included sgui1.6.1+1.21.1. JUnit tests plus actual Java/Bedrock protocol tests accompany the source. The built server JAR includes sgui; install Fabric API separately in a copy. Do not install into the live server from this prototype packet.

ROUTE_DECISION.md contains the primary-source comparison with Trinkets Polymer Port and NETS, transaction design and limitations. Source is preserved in this local Git repository; no remote push is claimed.
