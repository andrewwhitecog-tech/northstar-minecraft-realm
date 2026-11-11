scoreboard players set #after nspmg 0
scoreboard players reset #result nspmg
scoreboard players reset #success nspmg
execute store result score #result nspmg store success score #success nspmg run function nsp_crafter_refill:trim {x:935,y:66,z:-277,item:"iron_ingot"}
scoreboard players add #after nspmg 1
