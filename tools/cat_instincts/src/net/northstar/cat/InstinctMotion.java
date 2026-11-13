package net.northstar.cat;

/** Vanilla26.3 speed keys and bounded behaviour timing, independent of a Minecraft runtime. */
public final class InstinctMotion {
    public static final int HUNT_PRIORITY=5;
    public static final int BED_PRIORITY=7;
    public static final int PLAY_PRIORITY=10;
    public static final double STALK=0.6D;
    public static final double BURST=1.33D;
    private InstinctMotion() { }
    public static double huntSpeed(int elapsed,double distanceSquared) { return elapsed<12 && distanceSquared>4 ? STALK : BURST; }
    public static int playBeat(int elapsed) { return Math.floorMod(Math.floorDiv(elapsed,20),3); }
    public static double playSpeed(int beat) { return beat==0?STALK:beat==1?BURST:0.0D; }
    public static boolean distanceReturn(boolean active,double distanceSquared) { return distanceSquared>(active?256.0D:64.0D); }
}
