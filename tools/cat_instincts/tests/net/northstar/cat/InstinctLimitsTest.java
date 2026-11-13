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
    @Test void ReturnCorridorAdmitsCatAlreadyOutsideTheHuntDisk() {
        double catDistance=18;
        double corridor=InstinctLimits.returnPathRadiusSquared(catDistance*catDistance);
        assertTrue(corridor>=catDistance*catDistance,"The actual start node must be reachable on return");
        assertEquals(400.0,corridor,"A short detour is allowed without widening hunting");
        assertEquals(16,InstinctLimits.SEARCH_RADIUS);
    }
    @Test void ReturnCorridorRejectsUnboundedAndInvalidStarts() {
        assertEquals(256.0,InstinctLimits.returnPathRadiusSquared(4));
        assertEquals(4096.0,InstinctLimits.returnPathRadiusSquared(4096));
        for(double invalid:new double[]{-1,Double.NaN,Double.POSITIVE_INFINITY,4225})
            assertEquals(-1.0,InstinctLimits.returnPathRadiusSquared(invalid));
    }
}
