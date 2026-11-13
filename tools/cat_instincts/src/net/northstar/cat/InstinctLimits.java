package net.northstar.cat;

/** Pure live eligibility boundary, also exercised by unit tests. No invented runtime state. */
public final class InstinctLimits {
    public record State(boolean enabled, boolean adultTame, boolean ownerPresent,
                        boolean sitting, boolean leashed, boolean passenger, boolean noAi,
                        boolean recall, boolean healthy, boolean safeTerrain, boolean returnRequired) { }
    public static final int SEARCH_RADIUS=16;
    public static final int MAX_RETURN_DISTANCE=64;
    private InstinctLimits() { }
    /** A return route may begin outside the hunt disk; allow a2m detour, capped64m. */
    public static double returnPathRadiusSquared(double currentOwnerDistanceSquared) {
        if (!Double.isFinite(currentOwnerDistanceSquared) || currentOwnerDistanceSquared<0
            || currentOwnerDistanceSquared>MAX_RETURN_DISTANCE*MAX_RETURN_DISTANCE) return -1;
        double radius=Math.min(MAX_RETURN_DISTANCE,Math.max(SEARCH_RADIUS,Math.sqrt(currentOwnerDistanceSquared)+2));
        return radius*radius;
    }
    public static boolean mayPursue(State s) {
        return s.enabled() && s.adultTame() && s.ownerPresent() && !s.sitting() && !s.leashed()
            && !s.passenger() && !s.noAi() && !s.recall() && s.healthy() && s.safeTerrain() && !s.returnRequired();
    }
}
