package net.northstar.scopeprobe;

import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import com.google.gson.Gson;
import com.google.gson.JsonObject;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.animal.feline.Cat;
import net.minecraft.world.entity.ai.goal.Goal;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Isolated bench observer; no goal replacement or AI substitution. Contact requests
 * invoke the REAL transformed doHurtTarget only on bounded synthetic proof entities.
 */
@Mixin(Mob.class)
public abstract class ScopeObserverMixin {
 @Unique private static final Map<Goal,Integer> northstar$ids=new IdentityHashMap<>();
 @Unique private static int northstar$nextId;
 @Unique private static int northstar$lastAction;
 @Unique private static void northstar$write(Path path,Object value)throws Exception {
  Path tmp=path.resolveSibling(path.getFileName()+".tmp");
  Files.writeString(tmp,new Gson().toJson(value));
  Files.move(tmp,path,StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING);
 }
 @Unique private static boolean northstar$bounded(net.minecraft.world.entity.Entity e){
  return e.entityTags().contains("nsp_cat.proof") && e.getX()>=16 && e.getX()<=96 && e.getZ()>=16 && e.getZ()<=96 && e.getY()>=64 && e.getY()<=70;
 }
 @Inject(method="serverAiStep()V",at=@At("TAIL"),remap=false)
 private void northstar$observe(CallbackInfo ci){
  String configured=System.getProperty("nsp.cat.scope.probe.dir");
  if(configured==null || !((Object)this instanceof Cat cat) || !(cat.level() instanceof ServerLevel level) || !northstar$bounded(cat))return;
  Path root=Path.of(configured);
  try {
   if(!root.isAbsolute() || !Files.isDirectory(root) || Files.isSymbolicLink(root))throw new IllegalStateException("Existing absolute isolated observer root required");
   Map<String,Object> state=new LinkedHashMap<>();state.put("utc",Instant.now().toString());state.put("uuid",cat.getUUID().toString());
   state.put("catId",cat.getId());state.put("tick",level.getGameTime());state.put("tags",new TreeSet<>(cat.entityTags()));
   state.put("position",List.of(cat.getX(),cat.getY(),cat.getZ()));state.put("health",cat.getHealth());state.put("sitting",cat.isOrderedToSit());state.put("leashed",cat.isLeashed());
   state.put("ownerUuid",cat.getOwnerReference()==null?null:cat.getOwnerReference().getUUID().toString());
   state.put("implementsScopedCat",Class.forName("net.northstar.cat.ScopedCat").isInstance(cat));
   state.put("enabledProperty",Boolean.getBoolean("nsp.cat.instincts.enabled"));
   List<Object> goals=new ArrayList<>();
   for(var wrapped:cat.getGoalSelector().getAvailableGoals()){
    Goal goal=wrapped.getGoal();Integer id=northstar$ids.get(goal);
    if(id==null){if(northstar$ids.size()>=4096)throw new IllegalStateException("Bounded goal observation exceeded");id=++northstar$nextId;northstar$ids.put(goal,id);}
    goals.add(Map.of("objectId",id,"class",goal.getClass().getName(),"priority",wrapped.getPriority()));
   }
   state.put("goals",goals);
   Path first=root.resolve(cat.getUUID()+".first.json");
   if(!Files.exists(first))northstar$write(first,state);
   northstar$write(root.resolve(cat.getUUID()+".json"),state);
   Path action=root.resolve("action.json");
   if(Files.isRegularFile(action) && Files.size(action)<=4096){
    JsonObject request=new Gson().fromJson(Files.readString(action),JsonObject.class);
    int sequence=request.get("sequence").getAsInt();
    if(sequence>northstar$lastAction && request.get("catUuid").getAsString().equals(cat.getUUID().toString())){
     if(sequence!=northstar$lastAction+1 || !request.get("mode").getAsString().equals("contact"))throw new IllegalStateException("Unsupported or skipped action sequence");
     var target=level.getEntity(UUID.fromString(request.get("victimUuid").getAsString()));
     if(!(target instanceof LivingEntity victim) || !northstar$bounded(victim) || !victim.entityTags().contains("nsp_cat.proof.victim") || cat.distanceToSqr(victim)>9)throw new IllegalStateException("Exact bounded proof contact required");
     float before=victim.getHealth();boolean returned=cat.doHurtTarget(level,victim);float after=victim.getHealth();
     northstar$lastAction=sequence;
     northstar$write(root.resolve("CONTACT_ACTUAL.json"),Map.of("sequence",sequence,"catUuid",cat.getUUID().toString(),"victimUuid",victim.getUUID().toString(),"before",before,"after",after,"returned",returned,"tick",level.getGameTime(),"mechanism","Direct real transformed Mob.doHurtTarget call; NOT autonomous hunt proof"));
    }
   }
  }catch(Exception e){
   try{northstar$write(root.resolve("OBSERVER_ERROR.json"),Map.of("error",e.toString(),"utc",Instant.now().toString()));}catch(Exception ignored){}
   throw new IllegalStateException("Actual scoped cat observer failed",e);
  }
 }
}
