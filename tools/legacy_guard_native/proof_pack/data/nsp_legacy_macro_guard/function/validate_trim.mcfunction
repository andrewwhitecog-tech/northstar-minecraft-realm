data modify storage nsp_legacy_macro_guard:trim flags set value {valid:0b,x:0b,y:0b,z:0b,id:0b,changed:0b,id_length:0}
data modify storage nsp_legacy_macro_guard:trim canonical set value {x:0,y:0,z:0,id:""}
execute store success storage nsp_legacy_macro_guard:trim flags.x byte 1 store result storage nsp_legacy_macro_guard:trim canonical.x int 1 run data get storage nsp_legacy_macro_guard:trim raw.x
execute store success storage nsp_legacy_macro_guard:trim flags.y byte 1 store result storage nsp_legacy_macro_guard:trim canonical.y int 1 run data get storage nsp_legacy_macro_guard:trim raw.y
execute store success storage nsp_legacy_macro_guard:trim flags.z byte 1 store result storage nsp_legacy_macro_guard:trim canonical.z int 1 run data get storage nsp_legacy_macro_guard:trim raw.z
execute store result storage nsp_legacy_macro_guard:trim flags.id_length int 1 run data get storage nsp_legacy_macro_guard:trim raw.id
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:13} run function nsp_legacy_macro_guard:allow_trim_length_13
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:14} run function nsp_legacy_macro_guard:allow_trim_length_14
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:15} run function nsp_legacy_macro_guard:allow_trim_length_15
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:16} run function nsp_legacy_macro_guard:allow_trim_length_16
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:17} run function nsp_legacy_macro_guard:allow_trim_length_17
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:18} run function nsp_legacy_macro_guard:allow_trim_length_18
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:19} run function nsp_legacy_macro_guard:allow_trim_length_19
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:20} run function nsp_legacy_macro_guard:allow_trim_length_20
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:21} run function nsp_legacy_macro_guard:allow_trim_length_21
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:22} run function nsp_legacy_macro_guard:allow_trim_length_22
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:23} run function nsp_legacy_macro_guard:allow_trim_length_23
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:24} run function nsp_legacy_macro_guard:allow_trim_length_24
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:25} run function nsp_legacy_macro_guard:allow_trim_length_25
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:26} run function nsp_legacy_macro_guard:allow_trim_length_26
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:27} run function nsp_legacy_macro_guard:allow_trim_length_27
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:28} run function nsp_legacy_macro_guard:allow_trim_length_28
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:29} run function nsp_legacy_macro_guard:allow_trim_length_29
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:30} run function nsp_legacy_macro_guard:allow_trim_length_30
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:31} run function nsp_legacy_macro_guard:allow_trim_length_31
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:32} run function nsp_legacy_macro_guard:allow_trim_length_32
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:33} run function nsp_legacy_macro_guard:allow_trim_length_33
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:34} run function nsp_legacy_macro_guard:allow_trim_length_34
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:35} run function nsp_legacy_macro_guard:allow_trim_length_35
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:36} run function nsp_legacy_macro_guard:allow_trim_length_36
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:37} run function nsp_legacy_macro_guard:allow_trim_length_37
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:38} run function nsp_legacy_macro_guard:allow_trim_length_38
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:39} run function nsp_legacy_macro_guard:allow_trim_length_39
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:40} run function nsp_legacy_macro_guard:allow_trim_length_40
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:41} run function nsp_legacy_macro_guard:allow_trim_length_41
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:42} run function nsp_legacy_macro_guard:allow_trim_length_42
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:43} run function nsp_legacy_macro_guard:allow_trim_length_43
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:44} run function nsp_legacy_macro_guard:allow_trim_length_44
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:45} run function nsp_legacy_macro_guard:allow_trim_length_45
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:46} run function nsp_legacy_macro_guard:allow_trim_length_46
execute if data storage nsp_legacy_macro_guard:trim flags{id_length:48} run function nsp_legacy_macro_guard:allow_trim_length_48
execute unless data storage nsp_legacy_macro_guard:trim flags{x:1b,y:1b,z:1b,id:1b} run return 0
data modify storage nsp_legacy_macro_guard:trim canonical.id set from storage nsp_legacy_macro_guard:trim raw.id
execute unless data storage nsp_legacy_macro_guard:trim raw run return 0
execute unless data storage nsp_legacy_macro_guard:trim canonical run return 0
data modify storage nsp_legacy_macro_guard:trim compare set from storage nsp_legacy_macro_guard:trim raw
execute store success storage nsp_legacy_macro_guard:trim flags.changed byte 1 run data modify storage nsp_legacy_macro_guard:trim compare set from storage nsp_legacy_macro_guard:trim canonical
execute if data storage nsp_legacy_macro_guard:trim flags{changed:1b} run return 0
data modify storage nsp_legacy_macro_guard:trim expected_x set value {x:0}
data modify storage nsp_legacy_macro_guard:trim expected_x.x set from storage nsp_legacy_macro_guard:trim canonical.x
execute unless data storage nsp_legacy_macro_guard:trim coordinate_x run return 0
execute unless data storage nsp_legacy_macro_guard:trim expected_x run return 0
data modify storage nsp_legacy_macro_guard:trim compare set from storage nsp_legacy_macro_guard:trim coordinate_x
execute store success storage nsp_legacy_macro_guard:trim flags.changed byte 1 run data modify storage nsp_legacy_macro_guard:trim compare set from storage nsp_legacy_macro_guard:trim expected_x
execute if data storage nsp_legacy_macro_guard:trim flags{changed:1b} run return 0
data modify storage nsp_legacy_macro_guard:trim expected_y set value {y:0}
data modify storage nsp_legacy_macro_guard:trim expected_y.y set from storage nsp_legacy_macro_guard:trim canonical.y
execute unless data storage nsp_legacy_macro_guard:trim coordinate_y run return 0
execute unless data storage nsp_legacy_macro_guard:trim expected_y run return 0
data modify storage nsp_legacy_macro_guard:trim compare set from storage nsp_legacy_macro_guard:trim coordinate_y
execute store success storage nsp_legacy_macro_guard:trim flags.changed byte 1 run data modify storage nsp_legacy_macro_guard:trim compare set from storage nsp_legacy_macro_guard:trim expected_y
execute if data storage nsp_legacy_macro_guard:trim flags{changed:1b} run return 0
data modify storage nsp_legacy_macro_guard:trim expected_z set value {z:0}
data modify storage nsp_legacy_macro_guard:trim expected_z.z set from storage nsp_legacy_macro_guard:trim canonical.z
execute unless data storage nsp_legacy_macro_guard:trim coordinate_z run return 0
execute unless data storage nsp_legacy_macro_guard:trim expected_z run return 0
data modify storage nsp_legacy_macro_guard:trim compare set from storage nsp_legacy_macro_guard:trim coordinate_z
execute store success storage nsp_legacy_macro_guard:trim flags.changed byte 1 run data modify storage nsp_legacy_macro_guard:trim compare set from storage nsp_legacy_macro_guard:trim expected_z
execute if data storage nsp_legacy_macro_guard:trim flags{changed:1b} run return 0
data modify storage nsp_legacy_macro_guard:trim expected_pattern set value {id:""}
data modify storage nsp_legacy_macro_guard:trim expected_pattern.id set from storage nsp_legacy_macro_guard:trim canonical.id
execute unless data storage nsp_legacy_macro_guard:trim pattern run return 0
execute unless data storage nsp_legacy_macro_guard:trim expected_pattern run return 0
data modify storage nsp_legacy_macro_guard:trim compare set from storage nsp_legacy_macro_guard:trim pattern
execute store success storage nsp_legacy_macro_guard:trim flags.changed byte 1 run data modify storage nsp_legacy_macro_guard:trim compare set from storage nsp_legacy_macro_guard:trim expected_pattern
execute if data storage nsp_legacy_macro_guard:trim flags{changed:1b} run return 0
data modify storage nsp_legacy_macro_guard:trim flags.valid set value 1b
