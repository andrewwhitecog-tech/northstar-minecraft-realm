package net.northstar.cat;

import java.util.Comparator;
import java.util.EnumSet;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.animal.Animal;
import net.minecraft.world.entity.animal.feline.Cat;
import net.minecraft.world.level.pathfinder.Path;

/** Friendly approach/orbit/pause play. Never sets a combat target or invokes any damage API. */
public final class InstinctPlayGoal extends Goal {
    private final Cat cat;
    private LivingEntity companion;
    private int nextScanTick;
    private int started;
    private int nextMoveTick;
    private int turn;
    public InstinctPlayGoal(Cat cat) { this.cat=cat;setFlags(EnumSet.of(Flag.MOVE,Flag.LOOK)); }
    @Override public boolean requiresUpdateEveryTick() { return true; }
    @Override public boolean canUse() {
        if (!(cat.level() instanceof ServerLevel level) || !CatContext.mayPursue(cat) || cat.isInLove() || cat.getTarget()!=null || cat.tickCount<nextScanTick) return false;
        nextScanTick=cat.tickCount+80;
        var companions=level.getEntitiesOfClass(Animal.class,cat.getBoundingBox().inflate(8),a -> CatContext.mayPlay(cat,a));
        companions.sort(Comparator.comparingDouble(a -> cat.distanceToSqr(a)));
        companion=null;
        for (Animal candidate:companions.stream().limit(4).toList()) {
            Path path=cat.getNavigation().createPath(candidate,0);
            if (cat.hasLineOfSight(candidate) && CatContext.safePath(cat,path)) { companion=candidate;return true; }
        }
        return false;
    }
    @Override public void start() { started=cat.tickCount;nextMoveTick=started;turn=0;cat.setSprinting(false);cat.setLying(false);CatContext.playing(cat,true); }
    @Override public boolean canContinueToUse() {
        return companion!=null && CatContext.mayPlay(cat,companion) && !cat.isInLove() && cat.getTarget()==null
            && cat.tickCount-started<120 && cat.distanceToSqr(companion)<100;
    }
    @Override public void tick() {
        if (!canContinueToUse() || !(cat.level() instanceof ServerLevel level)) { stop();return; }
        cat.getLookControl().setLookAt(companion,20.0F,20.0F);
        if (cat.tickCount<nextMoveTick) return;
        nextMoveTick=cat.tickCount+20;
        // One pause in three gives the other animal room; no knockback or forced companion motion.
        int beat=InstinctMotion.playBeat(cat.tickCount-started);
        if (beat==2) { cat.getNavigation().stop();cat.setSprinting(false);cat.setLying(true);return; }
        cat.setLying(false);turn++;
        double angle=(turn%8)*Math.PI/4;
        BlockPos destination=BlockPos.containing(companion.getX()+Math.cos(angle)*2,companion.getY(),companion.getZ()+Math.sin(angle)*2);
        if (!CatContext.safeFeet(level,destination) || !cat.getNavigation().isStableDestination(destination)) { cat.getNavigation().stop();return; }
        Path path=cat.getNavigation().createPath(destination,0);
        if (CatContext.safePath(cat,path)) cat.getNavigation().moveTo(path,InstinctMotion.playSpeed(beat)); else cat.getNavigation().stop();
    }
    @Override public void stop() {
        companion=null;nextScanTick=cat.tickCount+160;
        cat.getNavigation().stop();cat.setSprinting(false);cat.setLying(false);CatContext.playing(cat,false);
    }
}
