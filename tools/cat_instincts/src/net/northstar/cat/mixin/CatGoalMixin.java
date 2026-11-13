package net.northstar.cat.mixin;

import java.util.ArrayList;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.ai.goal.CatLieOnBlockGoal;
import net.minecraft.world.entity.ai.goal.FollowOwnerGoal;
import net.minecraft.world.entity.animal.feline.Cat;
import net.minecraft.world.level.Level;
import net.northstar.cat.CatInstincts;
import net.northstar.cat.ScopedCat;
import net.northstar.cat.InstinctMotion;
import net.northstar.cat.InstinctVanillaFollowGoal;
import net.northstar.cat.InstinctHuntGoal;
import net.northstar.cat.InstinctPlayGoal;
import net.northstar.cat.InstinctReturnGoal;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;

/** Runtime scope is read after load, before selectors; no constructor-time pet opt-in. */
@Mixin(Cat.class)
public abstract class CatGoalMixin extends TamableAnimal implements ScopedCat {
    @Unique private boolean northstar$catGoalsAttached;
    @Unique private boolean northstar$scopeApplied;
    @Unique private Goal northstar$bed;
    @Unique private int northstar$bedPriority;
    @Unique private Goal northstar$follow;
    @Unique private int northstar$followPriority;
    @Unique private Goal northstar$scopedFollow;
    protected CatGoalMixin(EntityType<? extends TamableAnimal> type, Level level) { super(type,level); }
    @Inject(method="registerGoals()V",at=@At("TAIL"),remap=false)
    private void northstar$attachInstincts(CallbackInfo ci) {
        if (northstar$catGoalsAttached) return;
        northstar$catGoalsAttached=true;
        Cat cat=(Cat)(Object)this;
        // These goals cannot claim flags until the live scope+existing safety gates allow it.
        goalSelector.addGoal(3,new InstinctReturnGoal(cat));
        goalSelector.addGoal(InstinctMotion.HUNT_PRIORITY,new InstinctHuntGoal(cat));
        goalSelector.addGoal(InstinctMotion.PLAY_PRIORITY,new InstinctPlayGoal(cat));
    }
    @Override public void northstar$reconcileScope() {
        Cat cat=(Cat)(Object)this;
        boolean active=CatInstincts.active(cat);
        if (active==northstar$scopeApplied) return;
        if (active) {
            // Keep the original goal instances and ACTUAL priorities for exact removal/restore.
            for (var wrapped:new ArrayList<>(goalSelector.getAvailableGoals())) {
                Goal goal=wrapped.getGoal();
                if (northstar$bed==null && goal.getClass()==CatLieOnBlockGoal.class) {
                    northstar$bed=goal;northstar$bedPriority=wrapped.getPriority();
                    goalSelector.removeGoal(goal);goalSelector.addGoal(InstinctMotion.BED_PRIORITY,goal);
                } else if (northstar$follow==null && goal.getClass()==FollowOwnerGoal.class) {
                    northstar$follow=goal;northstar$followPriority=wrapped.getPriority();
                    northstar$scopedFollow=new InstinctVanillaFollowGoal(cat);
                    goalSelector.removeGoal(goal);goalSelector.addGoal(northstar$followPriority,northstar$scopedFollow);
                }
            }
        } else {
            // Do not overwrite a third-party replacement made after our scoped adjustment.
            if (northstar$bed!=null && northstar$hasGoal(northstar$bed,InstinctMotion.BED_PRIORITY)) {
                goalSelector.removeGoal(northstar$bed);goalSelector.addGoal(northstar$bedPriority,northstar$bed);
            }
            if (northstar$scopedFollow!=null && northstar$hasGoal(northstar$scopedFollow,northstar$followPriority)) {
                goalSelector.removeGoal(northstar$scopedFollow);
                if (goalSelector.getAvailableGoals().stream().noneMatch(w -> w.getGoal()==northstar$follow)) goalSelector.addGoal(northstar$followPriority,northstar$follow);
            }
            northstar$bed=null;northstar$follow=null;northstar$scopedFollow=null;
        }
        northstar$scopeApplied=active;
    }
    @Unique private boolean northstar$hasGoal(Goal goal,int priority) {
        return goalSelector.getAvailableGoals().stream().anyMatch(w -> w.getGoal()==goal && w.getPriority()==priority);
    }
}
