scoreboard players set #after nspmg 0
scoreboard players reset #result nspmg
scoreboard players reset #success nspmg
execute store result score #result nspmg store success score #success nspmg run function nsp_crafter_refill:trim {x:942,y:66,z:-277,item:"slime_ball"}
scoreboard players add #after nspmg 1
