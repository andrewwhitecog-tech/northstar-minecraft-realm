package net.northstar.cat;

import net.minecraft.world.entity.ai.goal.FollowOwnerGoal;
import net.minecraft.world.entity.animal.feline.Cat;

/** Preserve vanilla follow for kittens; enabled adult pets use validated walking return. */
public final class InstinctVanillaFollowGoal extends FollowOwnerGoal {
    private final Cat cat;
    public InstinctVanillaFollowGoal(Cat cat) { super(cat,1.0,10.0F,5.0F);this.cat=cat; }
    private boolean customReturn() { return CatInstincts.active(cat) && cat.isTame() && !cat.isBaby(); }
    @Override public boolean canUse() { return !customReturn() && super.canUse(); }
    @Override public boolean canContinueToUse() { return !customReturn() && super.canContinueToUse(); }
    @Override public void tick() { if (!customReturn()) super.tick(); }
}
