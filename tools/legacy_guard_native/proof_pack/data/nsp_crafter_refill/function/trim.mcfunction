$data modify storage nsp_legacy_macro_guard:trim raw set value {x:$(x),y:$(y),z:$(z),id:"minecraft:$(item)"}
$data modify storage nsp_legacy_macro_guard:trim coordinate_x set value {x:$(x)}
$data modify storage nsp_legacy_macro_guard:trim coordinate_y set value {y:$(y)}
$data modify storage nsp_legacy_macro_guard:trim coordinate_z set value {z:$(z)}
$data modify storage nsp_legacy_macro_guard:trim pattern set value {id:"minecraft:$(item)"}
function nsp_legacy_macro_guard:validate_trim
execute unless data storage nsp_legacy_macro_guard:trim flags{valid:1b} run return 0
# Keeps at most 16 stacks in an output barrel by clearing the lowest slots. Only the line's own output is removed: anything else in the first slot stops the trim, and the line waits.
# Items[0]{...} is not a valid path, so the first entry is copied to storage and tested there.
$data modify storage nsp_crafter_refill:t first set from block $(x) $(y) $(z) Items[0]
$execute if data block $(x) $(y) $(z) Items[16] if data storage nsp_crafter_refill:t first{id:"minecraft:$(item)"} run data remove block $(x) $(y) $(z) Items[0]
$data modify storage nsp_crafter_refill:t first set from block $(x) $(y) $(z) Items[0]
$execute if data block $(x) $(y) $(z) Items[16] if data storage nsp_crafter_refill:t first{id:"minecraft:$(item)"} run data remove block $(x) $(y) $(z) Items[0]
$data modify storage nsp_crafter_refill:t first set from block $(x) $(y) $(z) Items[0]
$execute if data block $(x) $(y) $(z) Items[16] if data storage nsp_crafter_refill:t first{id:"minecraft:$(item)"} run data remove block $(x) $(y) $(z) Items[0]
$data modify storage nsp_crafter_refill:t first set from block $(x) $(y) $(z) Items[0]
$execute if data block $(x) $(y) $(z) Items[16] if data storage nsp_crafter_refill:t first{id:"minecraft:$(item)"} run data remove block $(x) $(y) $(z) Items[0]
$data modify storage nsp_crafter_refill:t first set from block $(x) $(y) $(z) Items[0]
$execute if data block $(x) $(y) $(z) Items[16] if data storage nsp_crafter_refill:t first{id:"minecraft:$(item)"} run data remove block $(x) $(y) $(z) Items[0]
$data modify storage nsp_crafter_refill:t first set from block $(x) $(y) $(z) Items[0]
$execute if data block $(x) $(y) $(z) Items[16] if data storage nsp_crafter_refill:t first{id:"minecraft:$(item)"} run data remove block $(x) $(y) $(z) Items[0]
$data modify storage nsp_crafter_refill:t first set from block $(x) $(y) $(z) Items[0]
$execute if data block $(x) $(y) $(z) Items[16] if data storage nsp_crafter_refill:t first{id:"minecraft:$(item)"} run data remove block $(x) $(y) $(z) Items[0]
$data modify storage nsp_crafter_refill:t first set from block $(x) $(y) $(z) Items[0]
$execute if data block $(x) $(y) $(z) Items[16] if data storage nsp_crafter_refill:t first{id:"minecraft:$(item)"} run data remove block $(x) $(y) $(z) Items[0]
$data modify storage nsp_crafter_refill:t first set from block $(x) $(y) $(z) Items[0]
$execute if data block $(x) $(y) $(z) Items[16] if data storage nsp_crafter_refill:t first{id:"minecraft:$(item)"} run data remove block $(x) $(y) $(z) Items[0]
$data modify storage nsp_crafter_refill:t first set from block $(x) $(y) $(z) Items[0]
$execute if data block $(x) $(y) $(z) Items[16] if data storage nsp_crafter_refill:t first{id:"minecraft:$(item)"} run data remove block $(x) $(y) $(z) Items[0]
$data modify storage nsp_crafter_refill:t first set from block $(x) $(y) $(z) Items[0]
$execute if data block $(x) $(y) $(z) Items[16] if data storage nsp_crafter_refill:t first{id:"minecraft:$(item)"} run data remove block $(x) $(y) $(z) Items[0]
