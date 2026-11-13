package net.northstar.cat;

/** Pure live eligibility boundary, also exercised by unit tests. No invented runtime state. */
public final class InstinctLimits {
    public record State(boolean enabled, boolean adultTame, boolean ownerPresent,
                        boolean sitting, boolean leashed, boolean passenger, boolean noAi,
                        boolean recall, boolean healthy, boolean safeTerrain, boolean returnRequired) { }
    private InstinctLimits() { }
    public static boolean mayPursue(State s) {
        return s.enabled() && s.adultTame() && s.ownerPresent() && !s.sitting() && !s.leashed()
            && !s.passenger() && !s.noAi() && !s.recall() && s.healthy() && s.safeTerrain() && !s.returnRequired();
    }
}
