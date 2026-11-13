package net.northstar.cat;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

public class InstinctLimitsTest {
    private InstinctLimits.State state(int blocked) {
        return new InstinctLimits.State(blocked!=0,blocked!=1,blocked!=2,
            blocked==3,blocked==4,blocked==5,blocked==6,blocked==7,blocked!=8,blocked!=9,blocked==10);
    }
    @Test void HealthyOwnedUntetheredCatCanPursue() { assertTrue(InstinctLimits.mayPursue(state(-1))); }
    @Test void EachSafetyConditionIndependentlyPreemptsHuntingAndPlay() {
        String[] reasons={"disabled","not adult tame","owner absent","sitting","leashed","passenger","no AI","recall","low health","hazard","owner return"};
        for(int i=0;i<reasons.length;i++) assertFalse(InstinctLimits.mayPursue(state(i)),reasons[i]);
    }
    @Test void RecallCancelsAnAlreadyEligiblePursuitWithoutOverridingTheOwner() {
        assertTrue(InstinctLimits.mayPursue(state(-1)));
        assertFalse(InstinctLimits.mayPursue(state(7)));
        assertFalse(InstinctLimits.mayPursue(state(10)));
    }
}
