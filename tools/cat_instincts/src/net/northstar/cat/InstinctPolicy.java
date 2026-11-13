package net.northstar.cat;

/** Pure decision boundary used again at contact time, never a substitute for pathfinding. */
public final class InstinctPolicy {
    public enum Relation { PROTECTED, HOSTILE, WILD_PREY, PLAYMATE, UNKNOWN }
    public record Contact(boolean enabled, boolean adultTameCat, boolean sittingOrLeashed,
                          boolean sameWorld, boolean targetAlive, boolean player,
                          boolean owner, boolean pet, boolean friendlyNpc, boolean allied,
                          boolean protectedTag, boolean playable, boolean hostile,
                          boolean wildAnimal) {}
    private InstinctPolicy() {}
    public static Relation relation(Contact c) {
        if (!c.enabled() || !c.adultTameCat() || !c.sameWorld() || !c.targetAlive()) return Relation.PROTECTED;
        if (c.player() || c.owner() || c.pet() || c.friendlyNpc() || c.allied() || c.protectedTag())
            return c.playable() && !c.player() && !c.owner() && !c.friendlyNpc() ? Relation.PLAYMATE : Relation.PROTECTED;
        if (c.playable()) return Relation.PLAYMATE;
        if (c.hostile()) return Relation.HOSTILE;
        if (c.wildAnimal()) return Relation.WILD_PREY;
        return Relation.UNKNOWN;
    }
    public static boolean mayDamage(Contact c) {
        if (c.sittingOrLeashed()) return false;
        Relation r=relation(c);
        return r==Relation.HOSTILE || r==Relation.WILD_PREY;
    }
}
