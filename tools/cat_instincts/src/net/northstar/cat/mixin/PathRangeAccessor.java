package net.northstar.cat.mixin;

import net.minecraft.world.entity.ai.navigation.PathNavigation;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.gen.Accessor;

/** Snapshot the official path-length requirement so temporary return search restores it exactly. */
@Mixin(PathNavigation.class)
public interface PathRangeAccessor {
    @Accessor(value="requiredPathLength",remap=false)
    float northstar$getRequiredPathLength();
}
