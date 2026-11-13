package net.northstar.cat;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
public class InstinctMotionTest {
    @Test void StalkAndBurstMatchExactVanillaSpeedKeys() {
        assertEquals(0.6D,InstinctMotion.huntSpeed(0,100));assertEquals(0.6D,InstinctMotion.huntSpeed(11,100));
        assertEquals(1.33D,InstinctMotion.huntSpeed(12,100));assertEquals(1.33D,InstinctMotion.huntSpeed(25,9));
    }
    @Test void ActiveAndIdleReturnHaveDistinctOwnerCentredBounds() {
        assertFalse(InstinctMotion.distanceReturn(false,64));assertTrue(InstinctMotion.distanceReturn(false,65));
        assertFalse(InstinctMotion.distanceReturn(true,65));assertFalse(InstinctMotion.distanceReturn(true,256));assertTrue(InstinctMotion.distanceReturn(true,257));
        assertTrue(InstinctMotion.HUNT_PRIORITY<InstinctMotion.BED_PRIORITY);
        assertTrue(InstinctMotion.HUNT_PRIORITY>4);
    }
    @Test void PlayCyclesStalkDashAndStationaryBow() {
        assertEquals(0,InstinctMotion.playBeat(0));assertEquals(1,InstinctMotion.playBeat(20));assertEquals(2,InstinctMotion.playBeat(40));assertEquals(0,InstinctMotion.playBeat(60));
        assertEquals(0.6D,InstinctMotion.playSpeed(0));assertEquals(1.33D,InstinctMotion.playSpeed(1));assertEquals(0.0D,InstinctMotion.playSpeed(2));
    }
    @Test void OnlyAuthoritativeNaturalOriginsPermitNewWildClassification() {
        assertTrue(InstinctSpawnPolicy.naturalWildOrigin("NATURAL"));assertTrue(InstinctSpawnPolicy.naturalWildOrigin("CHUNK_GENERATION"));
        for(String s:new String[]{"BREEDING","COMMAND","BUCKET","SPAWN_ITEM_USE","LOAD","DIMENSION_TRAVEL","SPAWNER","STRUCTURE","natural",""}) assertFalse(InstinctSpawnPolicy.naturalWildOrigin(s),s);
        assertFalse(InstinctSpawnPolicy.naturalWildOrigin(null));
    }
}
