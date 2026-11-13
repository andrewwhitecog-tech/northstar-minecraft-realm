package net.northstar.cat;

import java.util.Set;
import java.util.Collections;
import java.util.WeakHashMap;
import net.minecraft.core.BlockPos;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityReference;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.OwnableEntity;
import net.minecraft.world.entity.TamableAnimal;
import net.minecraft.world.entity.animal.Animal;
import net.minecraft.world.entity.animal.equine.AbstractHorse;
import net.minecraft.world.entity.animal.feline.Cat;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.pathfinder.Node;
import net.minecraft.world.level.pathfinder.Path;

/** Converts ACTUAL current entities into policy facts; no remote/name-based trust grants. */
public final class CatContext {
    public static final int SEARCH_RADIUS = InstinctLimits.SEARCH_RADIUS;
    public static final int OWNER_RETURN_DISTANCE = 8;
    private static final Set<String> PROTECTED = Set.of(
        "nsp_cat.protected", "nsp_cat.no_hunt", "nsp_protected", "nsp_friendly", "nsp_npc",
        "nsp_pet", "nsp_owned", "nsp_managed", "nsp_livestock", "nsp_no_hunt");
    private static final Set<Cat> PLAYING=Collections.newSetFromMap(Collections.synchronizedMap(new WeakHashMap<Cat,Boolean>()));
    private CatContext() { }
    public static boolean engaged(Cat cat) { return cat.getTarget()!=null || PLAYING.contains(cat); }
    public static void playing(Cat cat,boolean value) { if(value)PLAYING.add(cat);else PLAYING.remove(cat); }

    public static LivingEntity owner(Cat cat) { return cat.getOwner(); }
    public static boolean healthy(Cat cat) { return cat.getHealth() > Math.max(4.0F, cat.getMaxHealth() * 0.5F); }
    public static boolean recall(Cat cat) { return cat.entityTags().contains("nsp_cat.recall"); }
    public static boolean protectedTag(Entity e) {
        return e.entityTags().stream().anyMatch(t -> PROTECTED.contains(t) || t.startsWith("nsp_npc") || t.startsWith("nsp_friendly"));
    }
    public static boolean pet(LivingEntity e) {
        return (e instanceof TamableAnimal tame && tame.isTame())
            || (e instanceof AbstractHorse horse && horse.isTamed())
            || (e instanceof OwnableEntity own && own.getOwnerReference() != null);
    }
    public static boolean sameOwner(Cat cat, LivingEntity target) {
        EntityReference<LivingEntity> ref = cat.getOwnerReference();
        return ref != null && ref.getUUID().equals(target.getUUID());
    }
    public static boolean npc(LivingEntity e) {
        return e.getType() == EntityTypes.VILLAGER || e.getType() == EntityTypes.WANDERING_TRADER
            || e.getType() == EntityTypes.IRON_GOLEM || e.getType() == EntityTypes.SNOW_GOLEM
            || (!(e instanceof Animal) && e.hasCustomName() && !e.entityTags().contains("nsp_cat.hostile"));
    }
    public static boolean managedAnimal(LivingEntity e) {
        return e instanceof Animal && (e.hasCustomName() || protectedTag(e) || (e instanceof Mob m && m.isLeashed()));
    }
    public static InstinctPolicy.Contact contact(Cat cat, LivingEntity target) {
        boolean allied = cat.isAlliedTo(target) || target.isAlliedTo(cat);
        boolean ownedPet = pet(target);
        boolean friendlyNpc = npc(target);
        boolean protectedTarget = protectedTag(target) || managedAnimal(target)
            || target.getType()==EntityTypes.CREEPER || target.getType()==EntityTypes.GHAST
            || target.getType()==EntityTypes.WARDEN || target.getType()==EntityTypes.WITHER || target.getType()==EntityTypes.ENDER_DRAGON;
        boolean hostile = target instanceof Enemy || target.entityTags().contains("nsp_cat.hostile");
        boolean playmate = target instanceof Animal && !friendlyNpc
            && (ownedPet || allied || protectedTarget || target.entityTags().contains("nsp_cat.playmate"));
        return new InstinctPolicy.Contact(CatInstincts.enabled(), cat.isTame() && !cat.isBaby(),
            cat.isOrderedToSit() || cat.isLeashed(),
            cat.level() == target.level(), target.isAlive(), target instanceof Player,
            sameOwner(cat,target), ownedPet, friendlyNpc, allied, protectedTarget, playmate,
            hostile, target instanceof Animal && target.entityTags().contains("nsp_cat.wild") && !ownedPet && !protectedTarget && !allied && !friendlyNpc);
    }
    public static boolean mayDamage(Cat cat, Entity target) {
        return target instanceof LivingEntity living && cat != living && mayPursue(cat)
            && InstinctPolicy.mayDamage(contact(cat,living));
    }
    public static boolean mayPlay(Cat cat, LivingEntity target) {
        return cat != target && mayPursue(cat) && InstinctPolicy.relation(contact(cat,target)) == InstinctPolicy.Relation.PLAYMATE;
    }
    public static InstinctLimits.State state(Cat cat) {
        LivingEntity o=owner(cat);
        boolean ownerPresent=o != null && o.isAlive() && cat.level()==o.level();
        return new InstinctLimits.State(CatInstincts.enabled(), cat.isTame() && !cat.isBaby(), ownerPresent,
            cat.isOrderedToSit(),cat.isLeashed(),cat.isPassenger(),cat.isNoAi(),
            recall(cat),healthy(cat),cat.level() instanceof ServerLevel level && safeFeet(level,cat.blockPosition()),
            ownerPresent && InstinctMotion.distanceReturn(engaged(cat),cat.distanceToSqr(o)));
    }
    public static boolean mayPursue(Cat cat) { return InstinctLimits.mayPursue(state(cat)); }
    public static boolean canReturn(Cat cat) {
        LivingEntity o=owner(cat);
        return CatInstincts.enabled() && cat.isTame() && !cat.isBaby() && o!=null && o.isAlive()
            && cat.level()==o.level() && !cat.isOrderedToSit() && !cat.isLeashed() && !cat.isPassenger() && !cat.isNoAi();
    }
    public static boolean returnNeeded(Cat cat) {
        LivingEntity o=owner(cat);
        return CatInstincts.enabled() && cat.isTame() && !cat.isBaby() && o != null && o.isAlive()
            && cat.level()==o.level() && !cat.isOrderedToSit()
            && !cat.isLeashed() && !cat.isPassenger() && !cat.isNoAi()
            && (recall(cat) || !healthy(cat) || InstinctMotion.distanceReturn(engaged(cat),cat.distanceToSqr(o)))
            && cat.distanceToSqr(o)>4;
    }
    /** PathNavigation defaults to16m; enlarge only this bounded search, then restore exact prior budget. */
    public static Path createReturnPath(Cat cat) {
        if (!canReturn(cat)) return null;
        double radiusSquared=InstinctLimits.returnPathRadiusSquared(cat.distanceToSqr(owner(cat)));
        if (radiusSquared<0) return null;
        var navigation=cat.getNavigation();
        float previous=((net.northstar.cat.mixin.PathRangeAccessor)navigation).northstar$getRequiredPathLength();
        if (!Float.isFinite(previous) || previous<0) return null;
        navigation.setRequiredPathLength(Math.max(previous,(float)Math.sqrt(radiusSquared)));
        try {
            Path path=navigation.createPath(owner(cat),1);
            if (safeReturnPath(cat,path)) return path;
            // A cached rejected owner path must not be reused on the next return attempt.
            if (path!=null && navigation.getPath()==path) navigation.stop();
            return null;
        } finally { navigation.setRequiredPathLength(previous); }
    }
    public static boolean safeFeet(ServerLevel level, BlockPos p) {
        if (!level.hasChunkAt(p) || !level.hasChunkAt(p.below())) return false;
        if (!level.getFluidState(p).isEmpty() || !level.getFluidState(p.below()).isEmpty()) return false;
        var at=level.getBlockState(p);var below=level.getBlockState(p.below());
        if (below.getCollisionShape(level,p.below()).isEmpty()) return false;
        for (var state : new net.minecraft.world.level.block.state.BlockState[]{at,below}) {
            if (state.is(Blocks.FIRE) || state.is(Blocks.SOUL_FIRE) || state.is(Blocks.LAVA)
                || state.is(Blocks.CACTUS) || state.is(Blocks.MAGMA_BLOCK) || state.is(Blocks.CAMPFIRE)
                || state.is(Blocks.SOUL_CAMPFIRE) || state.is(Blocks.SWEET_BERRY_BUSH)
                || state.is(Blocks.POWDER_SNOW) || state.is(Blocks.WITHER_ROSE)
                || state.is(Blocks.POINTED_DRIPSTONE)) return false;
        }
        return true;
    }
    public static boolean safePath(Cat cat, Path path) { return safePath(cat,path,false); }
    public static boolean safeReturnPath(Cat cat, Path path) { return safePath(cat,path,true); }
    private static boolean safePath(Cat cat, Path path, boolean returning) {
        if (!(cat.level() instanceof ServerLevel level) || path==null || !path.canReach() || path.getNodeCount()>128) return false;
        LivingEntity o=owner(cat);
        if (o==null || o.level()!=level) return false;
        double radiusSquared=returning?InstinctLimits.returnPathRadiusSquared(cat.distanceToSqr(o)):SEARCH_RADIUS*SEARCH_RADIUS;
        if(radiusSquared<0) return false;
        Node previous=null;
        for (int i=0;i<path.getNodeCount();i++) {
            Node n=path.getNode(i);BlockPos pos=new BlockPos(n.x,n.y,n.z);
            if (!safeFeet(level,pos) || (previous!=null && Math.abs(previous.y-n.y)>1)
                || o.distanceToSqr(n.x+0.5,n.y,n.z+0.5)>radiusSquared) return false;
            previous=n;
        }
        return true;
    }
    public static void halt(Cat cat) { cat.setTarget(null);cat.getNavigation().stop();cat.setSprinting(false);cat.setLying(false);playing(cat,false); }
}
