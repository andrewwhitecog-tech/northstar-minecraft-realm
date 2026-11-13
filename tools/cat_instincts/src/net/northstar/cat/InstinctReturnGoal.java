package net.northstar.cat;

import java.util.EnumSet;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.animal.feline.Cat;
import net.minecraft.world.level.pathfinder.Path;

/** Owner-directed normal navigation. No teleport/health/position setters. */
public final class InstinctReturnGoal extends Goal {
    private final Cat cat;
    private LivingEntity owner;
    private Path initial;
    private int nextPathTick;
    private int started;
    public InstinctReturnGoal(Cat cat) { this.cat=cat;setFlags(EnumSet.of(Flag.MOVE,Flag.LOOK)); }
    @Override public boolean requiresUpdateEveryTick() { return true; }
    @Override public boolean canUse() {
        if (!CatContext.returnNeeded(cat)) return false;
        owner=CatContext.owner(cat);
        initial=cat.getNavigation().createPath(owner,1);
        return CatContext.safePath(cat,initial);
    }
    @Override public void start() {
        CatContext.halt(cat);started=cat.tickCount;nextPathTick=started+10;
        cat.getNavigation().moveTo(initial,1.1);
    }
    @Override public boolean canContinueToUse() { return owner!=null && CatContext.canReturn(cat) && cat.distanceToSqr(owner)>4 && CatContext.owner(cat)==owner && cat.tickCount-started<200; }
    @Override public void tick() {
        if (!canContinueToUse()) { stop();return; }
        cat.setTarget(null);cat.setSprinting(false);cat.getLookControl().setLookAt(owner,30,30);
        if (cat.tickCount>=nextPathTick) {
            nextPathTick=cat.tickCount+10;
            Path path=cat.getNavigation().createPath(owner,1);
            if (CatContext.safePath(cat,path)) cat.getNavigation().moveTo(path,1.1); else cat.getNavigation().stop();
        }
    }
    @Override public void stop() { owner=null;initial=null;cat.getNavigation().stop();cat.setSprinting(false); }
}
