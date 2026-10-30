package net.northstar.gear;
import eu.pb4.sgui.api.GuiHelpers;
import net.minecraft.server.network.ServerPlayerEntity;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.injection.*;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfoReturnable;
@Mixin(ServerPlayerEntity.class)
public class DropGuard {
 @Inject(method="dropSelectedItem",at=@At("HEAD"),cancellable=true)
 private void northstar$blockDrop(boolean entireStack,CallbackInfoReturnable<Boolean> ci){if(GuiHelpers.getCurrentGui((ServerPlayerEntity)(Object)this) instanceof GearMenu)ci.setReturnValue(false);}
}
