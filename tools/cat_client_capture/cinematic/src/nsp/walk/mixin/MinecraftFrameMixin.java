package nsp.walk.mixin;

import net.minecraft.client.Minecraft;
import nsp.walk.RouteWalk;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Calls the recorder and the camera once per rendered frame, after the frame is finished. */
@Mixin(Minecraft.class)
abstract class MinecraftFrameMixin {
    @Inject(method = "renderFrame(Z)V", at = @At("HEAD"))
    private void nspOfflineHead(boolean advanceGameTime, CallbackInfo ci) {
        RouteWalk.beforeFrame((Minecraft)(Object)this);
    }
    @Inject(method = "renderFrame(Z)V", at = @At("TAIL"))
    private void nspWalkFrame(boolean advanceGameTime, CallbackInfo ci) {
        RouteWalk.onFrame((Minecraft) (Object) this);
    }
}
