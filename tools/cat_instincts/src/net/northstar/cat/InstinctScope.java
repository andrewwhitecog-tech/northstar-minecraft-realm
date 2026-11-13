package net.northstar.cat;

import java.util.Set;

/** The global feature flag alone never opts a public pet into custom behaviour. */
public final class InstinctScope {
    public static final String CANARY_TAG="nsp_cat.instincts.canary";
    private InstinctScope() { }
    public static boolean active(boolean enabled, boolean serverSide, boolean adultTame, Set<String> currentTags) {
        return enabled && serverSide && adultTame && currentTags!=null && currentTags.contains(CANARY_TAG);
    }
}
