scoreboard players set #after nspmg 0
scoreboard players reset #result nspmg
scoreboard players reset #success nspmg
execute store result score #result nspmg store success score #success nspmg run function nsp_crafter_refill:trim {x:725,y:73,z:153,item:"coal\"};say injected;{id:\"minecraft:coal"}
scoreboard players add #after nspmg 1
