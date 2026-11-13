package net.northstar.cat.mixin;

import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.animal.feline.Cat;
import net.northstar.cat.CatContext;
import net.northstar.cat.CatInstincts;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
import net.northstar.cat.ScopedCat;

/** Cat inherits this actual method. Revalidate relations immediately at damage contact. */
@Mixin(Mob.class)
public abstract class CatContactVetoMixin {
    // Actual26.3 Mob.serverAiStep() is final and runs before goal selectors.
    // Reconcile here, never in constructors while tags/owner NBT are still absent.
    @Inject(method="serverAiStep()V",at=@At("HEAD"),remap=false)
    private void northstar$prepareScopedGoals(CallbackInfo ci) {
        if ((Object)this instanceof ScopedCat scoped) scoped.northstar$reconcileScope();
    }

    @Inject(method="doHurtTarget(Lnet/minecraft/server/level/ServerLevel;Lnet/minecraft/world/entity/Entity;)Z",at=@At("HEAD"),cancellable=true,remap=false)
    private void northstar$denyProtectedContact(ServerLevel level,Entity target,CallbackInfoReturnable<Boolean> cir) {
        if (!((Object)this instanceof Cat cat) || !CatInstincts.active(cat)) return;
        if (!CatContext.mayDamage(cat,target)) { CatContext.halt(cat);cir.setReturnValue(false); }
    }
}
