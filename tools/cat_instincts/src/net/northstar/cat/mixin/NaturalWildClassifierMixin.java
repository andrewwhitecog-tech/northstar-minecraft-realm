package net.northstar.cat.mixin;

import net.minecraft.world.DifficultyInstance;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.SpawnGroupData;
import net.minecraft.world.entity.animal.Animal;
import net.minecraft.world.level.ServerLevelAccessor;
import net.northstar.cat.CatContext;
import net.northstar.cat.CatInstincts;
import net.northstar.cat.InstinctSpawnPolicy;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;

/** Optional real finalizeSpawn hook. Never migrates saved/unknown or command-created animals. */
@Mixin(Mob.class)
public abstract class NaturalWildClassifierMixin {
    @Inject(method="finalizeSpawn(Lnet/minecraft/world/level/ServerLevelAccessor;Lnet/minecraft/world/DifficultyInstance;Lnet/minecraft/world/entity/EntitySpawnReason;Lnet/minecraft/world/entity/SpawnGroupData;)Lnet/minecraft/world/entity/SpawnGroupData;",at=@At("RETURN"),remap=false)
    private void northstar$classifyNatural(ServerLevelAccessor world,DifficultyInstance difficulty,
            EntitySpawnReason reason,SpawnGroupData group,CallbackInfoReturnable<SpawnGroupData> cir) {
        if (!CatInstincts.enabled() || !Boolean.getBoolean("nsp.cat.instincts.classify-natural")) return;
        Mob mob=(Mob)(Object)this;
        if (!(mob instanceof Animal animal) || reason==null || !InstinctSpawnPolicy.naturalWildOrigin(reason.name())) return;
        if (CatContext.pet(animal) || CatContext.npc(animal) || CatContext.managedAnimal(animal)
            || CatContext.protectedTag(animal) || animal.getTeam()!=null || animal.isNoAi()) return;
        animal.addTag("nsp_cat.wild");
        animal.addTag("nsp_cat.wild.origin."+reason.name().toLowerCase(java.util.Locale.ROOT));
    }
}
