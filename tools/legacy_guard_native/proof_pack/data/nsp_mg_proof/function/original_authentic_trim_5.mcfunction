scoreboard players set #original_after nspmg 0
scoreboard players reset #original_result nspmg
scoreboard players reset #original_success nspmg
execute store result score #original_result nspmg store success score #original_success nspmg run function nsp_mg_proof:original_trim {x:942,y:66,z:-277,item:"slime_ball"}
scoreboard players add #original_after nspmg 1
