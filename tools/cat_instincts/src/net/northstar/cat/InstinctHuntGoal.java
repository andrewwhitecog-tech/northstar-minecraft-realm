package net.northstar.cat;

import java.util.Comparator;
import java.util.EnumSet;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.goal.Goal;
import net.minecraft.world.entity.animal.feline.Cat;
import net.minecraft.world.item.component.SwingAnimation;
import net.minecraft.world.level.pathfinder.Path;

/** Actual pathfinding/contact attacks, bounded to an owner-centred loaded neighbourhood. */
public final class InstinctHuntGoal extends Goal {
    private final Cat cat;
    private LivingEntity quarry;
    private Path initialPath;
    private int nextScanTick;
    private int started;
    private int nextPathTick;
    private int nextAttackTick;
    private int unseenSince=-1;
    private int pathFailures;
    private int retryUntil;
    private boolean hissed;
    public InstinctHuntGoal(Cat cat) { this.cat=cat;setFlags(EnumSet.of(Flag.MOVE,Flag.LOOK,Flag.TARGET,Flag.JUMP)); }
    @Override public boolean requiresUpdateEveryTick() { return true; }
    @Override public boolean canUse() {
        if (!(cat.level() instanceof ServerLevel level) || cat.tickCount<nextScanTick || !CatContext.mayPursue(cat)) return false;
        nextScanTick=cat.tickCount+20;
        quarry=null;initialPath=null;
        var candidates=level.getEntitiesOfClass(LivingEntity.class,cat.getBoundingBox().inflate(CatContext.SEARCH_RADIUS),
            e -> e!=cat && CatContext.mayDamage(cat,e));
        candidates.sort(Comparator.<LivingEntity>comparingInt(e -> InstinctPolicy.relation(CatContext.contact(cat,e))==InstinctPolicy.Relation.HOSTILE?0:1)
            .thenComparingDouble(e -> cat.distanceToSqr(e)));
        int attempted=0;
        for (LivingEntity candidate:candidates) {
            if (++attempted>8) break;
            if (!cat.hasLineOfSight(candidate) || !CatContext.safeFeet(level,candidate.blockPosition())) continue;
            Path path=cat.getNavigation().createPath(candidate,0);
            if (!CatContext.safePath(cat,path)) continue;
            quarry=candidate;initialPath=path;return true;
        }
        return false;
    }
    @Override public void start() {
        started=cat.tickCount;nextPathTick=started+10;nextAttackTick=started;unseenSince=-1;pathFailures=0;retryUntil=0;hissed=false;
        cat.setLying(false);
        cat.setTarget(quarry);
        cat.getNavigation().moveTo(initialPath,InstinctMotion.STALK);
    }
    @Override public boolean canContinueToUse() {
        return quarry!=null && CatContext.mayDamage(cat,quarry) && cat.getTarget()==quarry
            && cat.tickCount-started<=400 && cat.distanceToSqr(quarry)<=CatContext.SEARCH_RADIUS*CatContext.SEARCH_RADIUS
            && (unseenSince<0 || cat.tickCount-unseenSince<=40) && pathFailures<3;
    }
    @Override public void tick() {
        // Recheck live relationships and safety before movement AND immediately before every hit.
        if (!canContinueToUse() || !(cat.level() instanceof ServerLevel level)) { stop();return; }
        if (cat.hasLineOfSight(quarry)) unseenSince=-1; else if (unseenSince<0) unseenSince=cat.tickCount;
        cat.getLookControl().setLookAt(quarry,30.0F,30.0F);
        if (cat.tickCount>=nextPathTick) {
            nextPathTick=cat.tickCount+10;
            Path path=cat.getNavigation().createPath(quarry,0);
            if (!CatContext.safeFeet(level,quarry.blockPosition()) || !CatContext.safePath(cat,path)) {
                pathFailures++;cat.getNavigation().stop();cat.setSprinting(false);retryUntil=cat.tickCount+10;
            } else { pathFailures=0;cat.getNavigation().moveTo(path,InstinctMotion.huntSpeed(cat.tickCount-started,cat.distanceToSqr(quarry))); }
        }
        Path active=cat.getNavigation().getPath();
        if (active!=null && !CatContext.safePath(cat,active)) { pathFailures++;cat.getNavigation().stop();cat.setSprinting(false);retryUntil=cat.tickCount+10;return; }
        if (cat.tickCount<retryUntil) return;
        double speed=InstinctMotion.huntSpeed(cat.tickCount-started,cat.distanceToSqr(quarry));
        cat.setLying(false);
        if (active!=null) cat.getNavigation().moveTo(active,speed);
        if (!hissed && speed==InstinctMotion.BURST && InstinctPolicy.relation(CatContext.contact(cat,quarry))==InstinctPolicy.Relation.HOSTILE) { cat.hiss();hissed=true; }
        if (cat.tickCount>=nextAttackTick && cat.hasLineOfSight(quarry)
            && cat.isWithinMeleeAttackRange(quarry) && CatContext.mayDamage(cat,quarry)) {
            nextAttackTick=cat.tickCount+20;
            cat.swing(InteractionHand.MAIN_HAND,SwingAnimation.DEFAULT);
            cat.doHurtTarget(level,quarry);
        }
    }
    @Override public void stop() {
        quarry=null;initialPath=null;
        nextScanTick=cat.tickCount+40;
        CatContext.halt(cat);
    }
}
