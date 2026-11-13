package net.northstar.cat.mixin;

import java.util.ArrayList;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.ai.goal.CatLieOnBlockGoal;
import net.northstar.cat.CatInstincts;
import net.northstar.cat.InstinctMotion;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.entity.animal.feline.Cat;
import net.minecraft.world.level.Level;
import net.northstar.cat.InstinctHuntGoal;
import net.northstar.cat.InstinctPlayGoal;
import net.northstar.cat.InstinctReturnGoal;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Attach once at vanilla goal registration; eligibility reads restored tame/owner state later. */
@Mixin(Cat.class)
public abstract class CatGoalMixin extends TamableAnimal {
    @Unique private boolean northstar$catGoalsAttached;
    protected CatGoalMixin(EntityType<? extends TamableAnimal> type, Level level) { super(type,level); }
    @Inject(method="registerGoals()V",at=@At("TAIL"),remap=false)
    private void northstar$attachInstincts(CallbackInfo ci) {
        if (northstar$catGoalsAttached) return;
        northstar$catGoalsAttached=true;
        Cat cat=(Cat)(Object)this;
        // Float/panic1 and ordered sit2 stay dominant; owner return3 beats autonomous behaviour.
        goalSelector.addGoal(3,new InstinctReturnGoal(cat));
        // Equal priority never replaces a running goal: move only vanilla bed-rest below hunt5.
        if (CatInstincts.enabled()) {
            for (var wrapped:new ArrayList<>(goalSelector.getAvailableGoals())) {
                if (wrapped.getGoal() instanceof CatLieOnBlockGoal) {
                    var bed=wrapped.getGoal();goalSelector.removeGoal(bed);goalSelector.addGoal(InstinctMotion.BED_PRIORITY,bed);
                }
            }
        }
        goalSelector.addGoal(InstinctMotion.HUNT_PRIORITY,new InstinctHuntGoal(cat));
        // Play yields to follow6, sitting7, hunting8 and breeding10; may replace random stroll11.
        goalSelector.addGoal(InstinctMotion.PLAY_PRIORITY,new InstinctPlayGoal(cat));
    }
}
