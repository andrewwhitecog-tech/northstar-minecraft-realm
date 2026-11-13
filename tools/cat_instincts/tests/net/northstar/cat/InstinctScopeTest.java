package net.northstar.cat;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Scope/eligibility/contact regressions on the production decisions. NBT/native lifecycle separate. */
public class InstinctScopeTest {
    private boolean active(boolean enabled,boolean server,boolean adultTame,Set<String> tags) {
        return InstinctScope.active(enabled,server,adultTame,tags);
    }
    private InstinctLimits.State pursuit(boolean scoped) {
        return new InstinctLimits.State(scoped,true,true,false,false,false,false,false,true,true,false);
    }
    private InstinctPolicy.Contact target(boolean scoped,boolean player,boolean owner,boolean pet,boolean npc,boolean ally,boolean protectedTag) {
        return new InstinctPolicy.Contact(scoped,true,false,true,true,player,owner,pet,npc,ally,protectedTag,false,true,true);
    }
    @Test void globalEnableNeverOptsAnUntaggedOrMisTaggedPetIn() {
        for (var tags:List.of(Set.<String>of(),Set.of("nsp_cat.protected"),Set.of("nsp_cat.instincts.canary.extra"),Set.of("NSP_CAT.INSTINCTS.CANARY"))) {
            assertFalse(active(true,true,true,tags));
            assertFalse(InstinctLimits.mayPursue(pursuit(active(true,true,true,tags))));
        }
        assertFalse(active(true,true,true,null));
    }
    @Test void explicitScopeStillRequiresFeatureServerAndAdultTame() {
        Set<String> tag=Set.of(InstinctScope.CANARY_TAG);
        assertTrue(active(true,true,true,tag));
        assertFalse(active(false,true,true,tag));
        assertFalse(active(true,false,true,tag));
        assertFalse(active(true,true,false,tag));
        assertTrue(InstinctLimits.mayPursue(pursuit(active(true,true,true,tag))));
    }
    @Test void scopeIsReadAfterRestoredTagsAndAgainAfterRevocationNotCachedAtConstruction() {
        Set<String> current=new HashSet<>();
        assertFalse(active(true,true,true,current));
        // Models an authentic restored tag collection, not an NBT/save acceptance claim.
        current.addAll(List.of(InstinctScope.CANARY_TAG,"unrelated.saved.tag"));
        assertTrue(active(true,true,true,current));
        Set<String> reloaded=new HashSet<>(current);
        assertTrue(active(true,true,true,reloaded));
        reloaded.remove(InstinctScope.CANARY_TAG);
        assertFalse(active(true,true,true,reloaded));
        assertFalse(InstinctLimits.mayPursue(pursuit(active(true,true,true,reloaded))));
        assertTrue(current.contains(InstinctScope.CANARY_TAG));
    }
    @Test void contactRevalidatesRevocationAfterAPreviouslyEligibleTarget() {
        Set<String> tags=new HashSet<>(Set.of(InstinctScope.CANARY_TAG));
        assertTrue(InstinctPolicy.mayDamage(target(active(true,true,true,tags),false,false,false,false,false,false)));
        tags.clear();
        assertFalse(InstinctPolicy.mayDamage(target(active(true,true,true,tags),false,false,false,false,false,false)));
    }
    @Test void scopedTargetCannotOverrideAnyFriendshipExclusion() {
        boolean scoped=active(true,true,true,Set.of(InstinctScope.CANARY_TAG));
        for (int category=0;category<6;category++)
            assertFalse(InstinctPolicy.mayDamage(target(scoped,category==0,category==1,category==2,category==3,category==4,category==5)));
    }
    @Test void scopedGoalsStillYieldToSitLeashRecallLowHealthAndMissingOwner() {
        boolean s=active(true,true,true,Set.of(InstinctScope.CANARY_TAG));
        for (var state:new InstinctLimits.State[]{
                new InstinctLimits.State(s,true,true,true,false,false,false,false,true,true,false),
                new InstinctLimits.State(s,true,true,false,true,false,false,false,true,true,false),
                new InstinctLimits.State(s,true,true,false,false,false,false,true,true,true,false),
                new InstinctLimits.State(s,true,true,false,false,false,false,false,false,true,false),
                new InstinctLimits.State(s,true,false,false,false,false,false,false,true,true,false)})
            assertFalse(InstinctLimits.mayPursue(state));
    }
}
