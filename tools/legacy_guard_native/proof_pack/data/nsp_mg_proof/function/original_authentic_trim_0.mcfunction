scoreboard players set #original_after nspmg 0
scoreboard players reset #original_result nspmg
scoreboard players reset #original_success nspmg
execute store result score #original_result nspmg store success score #original_success nspmg run function nsp_mg_proof:original_trim {x:725,y:73,z:153,item:"coal"}
scoreboard players add #original_after nspmg 1
