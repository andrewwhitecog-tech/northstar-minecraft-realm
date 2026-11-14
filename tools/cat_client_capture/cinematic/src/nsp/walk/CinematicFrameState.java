package nsp.walk;

/** Pure single-frame ownership/order protocol; no clock, game, GPU or filesystem access. */
public final class CinematicFrameState {
    public enum Phase { READY, RENDER, GPU, WRITE, COMPLETE, FAILED }
    public record Pose(double x,double y,double z,float yaw,float pitch) {
        public Pose { if (!Double.isFinite(x)||!Double.isFinite(y)||!Double.isFinite(z)||!Float.isFinite(yaw)||!Float.isFinite(pitch)) throw new IllegalArgumentException("nonfinite pose"); }
    }
    public record Ticket(int index,long renderId,Pose pose) {}
    private final int frames;
    private final long started,totalBudget,frameBudget;
    private long pendingSince,lastRender;
    private int committed;
    private Phase phase=Phase.READY;
    private Ticket pending;
    private String error;
    public CinematicFrameState(int frames,long now,long totalBudget,long frameBudget) {
        if(frames<2||frames>600||totalBudget<=0||frameBudget<=0||frameBudget>totalBudget) throw new IllegalArgumentException("finite frame/deadline bounds");
        this.frames=frames;this.started=now;this.totalBudget=totalBudget;this.frameBudget=frameBudget;
    }
    public synchronized void check(long now) {
        if(phase==Phase.COMPLETE||phase==Phase.FAILED)return;
        if(now-started>=totalBudget)fail("overall deadline");
        else if(pending!=null&&now-pendingSince>=frameBudget)fail("pending frame deadline");
    }
    /** RAM must already be exclusively reserved before this render ticket is admitted. */
    public synchronized Ticket begin(long renderId,Pose pose,boolean ramReserved,long now) {
        check(now);if(phase!=Phase.READY)return null;
        if(!ramReserved){fail("RAM not reserved before rendering");return null;}
        if(renderId<=lastRender){fail("render identity order");return null;}
        pending=new Ticket(committed,renderId,pose);lastRender=renderId;pendingSince=now;phase=Phase.RENDER;return pending;
    }
    private boolean expect(Ticket t,Phase wanted) {
        if(phase==Phase.FAILED)return false;
        if(phase!=wanted||t==null||!t.equals(pending)){fail("wrong ticket or phase: "+wanted);return false;}return true;
    }
    /** Release an unsubmitted render only. IDs and global deadline are never rewound. */
    public synchronized boolean deferRender(Ticket t,long now) {
        check(now);if(!expect(t,Phase.RENDER))return false;
        pending=null;phase=Phase.READY;return true;
    }
    public synchronized boolean rendering(Ticket t){return phase==Phase.RENDER&&t!=null&&t.equals(pending);}
    public synchronized boolean rendered(Ticket t,Pose actual,long now) {
        check(now);if(!expect(t,Phase.RENDER))return false;
        if(!t.pose().equals(actual)){fail("rendered pose differs from HEAD pose");return false;}
        phase=Phase.GPU;return true;
    }
    public synchronized boolean copied(Ticket t,long now) {check(now);if(!expect(t,Phase.GPU))return false;phase=Phase.WRITE;return true;}
    /** Called only after both actual raw write/flush and actual index write/flush succeed. */
    public synchronized boolean committed(Ticket t,long now) {
        check(now);if(!expect(t,Phase.WRITE))return false;
        committed++;pending=null;phase=committed==frames?Phase.COMPLETE:Phase.READY;return true;
    }
    public synchronized void fail(String why){if(error==null)error=why;phase=Phase.FAILED;}
    public synchronized boolean writable(Ticket t){return phase==Phase.WRITE&&t!=null&&t.equals(pending);}
    public synchronized int index(){return committed;}
    public synchronized int count(){return frames;}
    public synchronized Phase phase(){return phase;}
    public synchronized String error(){return error;}
}
