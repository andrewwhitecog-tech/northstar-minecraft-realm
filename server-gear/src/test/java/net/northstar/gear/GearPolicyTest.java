package net.northstar.gear;
import org.junit.jupiter.api.Test;import static org.junit.jupiter.api.Assertions.*;import java.util.*;
class GearPolicyTest {
 @Test void allRequestedCapacities(){assertArrayEquals(new int[]{9,18,27,54},Arrays.stream(new int[]{0,1,2,3}).map(GearPolicy::capacity).toArray());assertThrows(IllegalArgumentException.class,()->GearPolicy.capacity(-1));assertThrows(IllegalArgumentException.class,()->GearPolicy.capacity(4));}
 @Test void nestedStorageIsRejected(){for(String kind:List.of("backpack","pouch"))assertFalse(GearPolicy.accepts(false,0,kind,""));assertTrue(GearPolicy.accepts(false,0,"",""));}
 @Test void accessorySlotsAreTyped(){for(int slot=0;slot<4;slot++)for(String kind:List.of("ring","amulet","charm","backpack","pouch","")){boolean expected=slot<2?kind.equals("ring"):slot==2?kind.equals("amulet"):kind.equals("charm");assertEquals(expected,GearPolicy.accepts(true,slot,kind,""));}}
 @Test void holderAndSwapDupePathsAreBlocked(){for(String action:List.of("SWAP","CLONE","PICKUP_ALL","THROW","QUICK_MOVE","PICKUP","QUICK_CRAFT"))assertFalse(GearPolicy.actionAllowed(action,true));for(String action:List.of("SWAP","CLONE","PICKUP_ALL"))assertFalse(GearPolicy.actionAllowed(action,false));for(String action:List.of("THROW","QUICK_MOVE","PICKUP","QUICK_CRAFT"))assertTrue(GearPolicy.actionAllowed(action,false));}
 @Test void identicalRingsCannotAmplify(){assertEquals(Set.of("strider","night_eye"),GearPolicy.activeEffects(List.of("strider","strider","night_eye","")));}
 @Test void completeFirstSet(){assertEquals(9,GearPolicy.RINGS.size());assertEquals(9,new HashSet<>(GearPolicy.RINGS).size());assertEquals(List.of("copper","iron","gold","netherite","vorath"),GearPolicy.BANDS);}
}
