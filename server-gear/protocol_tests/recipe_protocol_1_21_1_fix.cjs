// Scoped fix for upstream minecraft-data PR1291, not yet merged.
// https://github.com/PrismarineJS/minecraft-data/pull/1291
// Verified exact upstream head e27f32c998ab2618230e521bbf54844910798c19.
// Must load BEFORE Minecraft client/serializer construction; never suppress parse errors.
const {createHash}=require('node:crypto');
const data=require('minecraft-data')('1.21.1');
const types=data.protocol.play.toClient.types;
const hash=v=>createHash('sha256').update(JSON.stringify(v)).digest('hex');
const current=hash(types.packet_declare_recipes);
if(current==='f3d44b0e5c98d99fe56f0c68cfcf4e8f458b936e97c0fd617235f9c237f88012') { module.exports={applied:false,alreadyFixed:true}; }
else {
 if(current!=='b14e51524e58d20ebd5f16143f3aa559a8a50803d164dada1474f0a4a91b4694') throw Error('Unexpected 1.21.1 recipe schema: '+current);
 const fixed=structuredClone(types.packet_declare_recipes);
 const fields=fixed[1][0].type[1].type[1];
 const map=fields.find(x=>x.name==='type').type[1].mappings;
 if(map[11]!=='minecraft:crafting_special_banneraddpattern')throw Error('Recipe ID guard failed');
 for(let id=11;id<=22;id++)map[id]=map[id+1];
 delete map[23];
 delete fields.find(x=>x.name==='data').type[1].fields['minecraft:crafting_special_banneraddpattern'];
 if(hash(fixed)!=='f3d44b0e5c98d99fe56f0c68cfcf4e8f458b936e97c0fd617235f9c237f88012')throw Error('Fixed recipe schema hash mismatch');
 types.packet_declare_recipes=fixed;
 module.exports={applied:true,upstream:'e27f32c998ab2618230e521bbf54844910798c19',sha256:hash(fixed)};
}
