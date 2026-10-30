package net.northstar.gear;
import java.util.*;
/** Pure policy shared by server code and JUnit. No client assumptions. */
public final class GearPolicy {
 public static final int[] CAPACITIES={9,18,27,54};
 public static int capacity(int tier){if(tier<0||tier>3)throw new IllegalArgumentException("Invalid tier");return CAPACITIES[tier];}
 public static boolean accepts(boolean pouch,int slot,String kind,String effect){
  if(!pouch)return !Set.of("backpack","pouch").contains(kind);
  return slot<2 ? kind.equals("ring") : slot==2 ? kind.equals("amulet") : slot==3 && kind.equals("charm");
 }
 public static boolean actionAllowed(String action,boolean holder){return !holder&&!Set.of("SWAP","CLONE","PICKUP_ALL").contains(action);}
 public static Set<String> activeEffects(List<String> effects){var result=new HashSet<String>();for(String s:effects)if(!s.isEmpty())result.add(s);return result;}
 public static final List<String> RINGS=List.of("night_eye","strider","miners_band","tidebreath","ember_ward","lodestone","lantern","hearth","luck_of_the_fold");
 public static final List<String> BANDS=List.of("copper","iron","gold","netherite","vorath");
 private GearPolicy(){}
}
