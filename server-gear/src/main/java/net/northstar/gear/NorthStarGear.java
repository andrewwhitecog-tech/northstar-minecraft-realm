package net.northstar.gear;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.player.UseItemCallback;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.command.CommandManager;
import net.minecraft.command.argument.EntityArgumentType;
import net.minecraft.item.*;
import net.minecraft.entity.*;
import net.minecraft.entity.effect.*;
import net.minecraft.registry.entry.RegistryEntry;
import net.minecraft.text.Text;
import net.minecraft.util.*;
import net.minecraft.util.math.*;
import net.minecraft.component.*;
import net.minecraft.component.type.*;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import java.util.*;
public final class NorthStarGear implements ModInitializer {
 private static final Map<UUID,Vec3d> positions=new HashMap<>();
 private static final Map<UUID,Integer> still=new HashMap<>(),lava=new HashMap<>();
 private int ticks=0;
 public void onInitialize(){
  CommandRegistrationCallback.EVENT.register((d,r,e)->{
   d.register(CommandManager.literal("backpack").executes(c->{open(c.getSource().getPlayerOrThrow(),"backpack");return 1;}));
   d.register(CommandManager.literal("accessories").executes(c->{open(c.getSource().getPlayerOrThrow(),"pouch");return 1;}));
   d.register(CommandManager.literal("ringwright").executes(c->{Ringwright.open(c.getSource().getPlayerOrThrow());return 1;}));
   d.register(CommandManager.literal("nspgear").requires(s->s.hasPermissionLevel(2))
    .then(CommandManager.literal("give").then(CommandManager.argument("player",EntityArgumentType.player()).then(CommandManager.argument("kind",StringArgumentType.word()).then(CommandManager.argument("tier",IntegerArgumentType.integer(0,3)).then(CommandManager.argument("effect",StringArgumentType.word()).executes(c->{var p=EntityArgumentType.getPlayer(c,"player");String kind=StringArgumentType.getString(c,"kind");String eff=StringArgumentType.getString(c,"effect");if(!Set.of("backpack","pouch","ring","amulet","charm").contains(kind))return 0;Ringwright.output(p,GearItems.make(kind,IntegerArgumentType.getInteger(c,"tier"),eff.equals("none")?"":eff));return 1;}))))))
    .then(CommandManager.literal("audit").then(CommandManager.argument("player",EntityArgumentType.player()).executes(c->{String report=RuntimeChecks.audit(EntityArgumentType.getPlayer(c,"player"));c.getSource().sendFeedback(()->Text.literal(report),false);return 1;})))
    .then(CommandManager.literal("selftest").executes(c->{String report=RuntimeChecks.run(c.getSource().getServer());c.getSource().sendFeedback(()->Text.literal(report),false);return 1;})));
  });
  UseItemCallback.EVENT.register((p,w,h)->{if(!w.isClient&&p instanceof ServerPlayerEntity s&&GearItems.storage(p.getStackInHand(h))){int slot=h==Hand.MAIN_HAND?s.getInventory().selectedSlot:40;new GearMenu(s,slot).open();return TypedActionResult.success(p.getStackInHand(h));}return TypedActionResult.pass(p.getStackInHand(h));});
  ServerTickEvents.END_SERVER_TICK.register(server->{for(var p:server.getPlayerManager().getPlayerList())lava.put(p.getUuid(),p.isInLava()?lava.getOrDefault(p.getUuid(),0)+1:0);if(++ticks%20==0)tick(server);});
  ServerLifecycleEvents.SERVER_STARTED.register(LanternLights::recover);
  ServerLifecycleEvents.SERVER_STOPPING.register(LanternLights::clear);
 }
 static void open(ServerPlayerEntity p,String kind){if(p.currentScreenHandler!=p.playerScreenHandler)p.closeHandledScreen();for(int i=0;i<p.getInventory().size();i++)if(GearItems.kind(p.getInventory().getStack(i)).equals(kind)){new GearMenu(p,i).open();return;}p.sendMessage(Text.literal("Craft a "+(kind.equals("pouch")?"pouch":"backpack")+" at /ringwright first."),false);}
 static void status(ServerPlayerEntity p,RegistryEntry<StatusEffect> e){p.addStatusEffect(new StatusEffectInstance(e,e==StatusEffects.NIGHT_VISION?260:45,0,true,false,true));}
 private void tick(MinecraftServer server){
  LanternLights.clear(server);var connected=new HashSet<UUID>();
  for(var p:server.getPlayerManager().getPlayerList()){
   UUID id=p.getUuid();connected.add(id);if(!p.isAlive())continue;
   Vec3d previous=positions.put(id,p.getPos());int resting=previous!=null&&previous.squaredDistanceTo(p.getPos())<0.0025?still.getOrDefault(id,0)+1:0;still.put(id,resting);
   int burning=lava.getOrDefault(id,0);
   ItemStack pouch=ItemStack.EMPTY;for(int i=0;i<p.getInventory().size();i++){var s=p.getInventory().getStack(i);if(GearItems.kind(s).equals("pouch")){pouch=s;break;}}
   var contents=GearItems.contents(pouch,4);Set<String> active=new HashSet<>();for(int i=0;i<4;i++){var s=contents.get(i);if(GearPolicy.accepts(true,i,GearItems.kind(s),GearItems.effect(s)))active.add(GearItems.effect(s));}
   for(String effect:active)switch(effect){
    case "night_eye"->status(p,StatusEffects.NIGHT_VISION);case "strider"->status(p,StatusEffects.SPEED);case "miners_band"->status(p,StatusEffects.HASTE);case "tidebreath"->status(p,StatusEffects.WATER_BREATHING);case "luck_of_the_fold"->status(p,StatusEffects.LUCK);case "slowfall"->status(p,StatusEffects.SLOW_FALLING);
    case "ember_ward"->{if(burning>=60)status(p,StatusEffects.FIRE_RESISTANCE);}
    case "hearth"->{if(resting>=5&&resting%10==0&&!p.getHungerManager().isNotFull())p.heal(1);}
    case "lodestone"->{for(ItemEntity entity:p.getServerWorld().getEntitiesByClass(ItemEntity.class,p.getBoundingBox().expand(6),e->e.isAlive()&&e.squaredDistanceTo(p)<=36)){var direction=p.getPos().add(0,0.5,0).subtract(entity.getPos());entity.setVelocity(direction.normalize().multiply(0.25));entity.velocityModified=true;}}
    case "lantern"->LanternLights.place(p);
    case "spectral_sight"->{for(LivingEntity mob:p.getServerWorld().getEntitiesByClass(LivingEntity.class,p.getBoundingBox().expand(12),e->!(e instanceof ServerPlayerEntity)&&e.squaredDistanceTo(p)<=144).stream().limit(32).toList())mob.addStatusEffect(new StatusEffectInstance(StatusEffects.GLOWING,25,0,true,false));}
   }
  }
  positions.keySet().retainAll(connected);still.keySet().retainAll(connected);lava.keySet().retainAll(connected);LanternLights.save(server);
 }
}
