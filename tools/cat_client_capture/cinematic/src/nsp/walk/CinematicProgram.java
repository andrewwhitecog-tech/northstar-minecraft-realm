package nsp.walk;

/** Explicit offline camera program: one authored pose for each committed output index. */
public final class CinematicProgram {
    public final int fps,frames;
    public final String mode;
    private final double[] p;
    public static boolean allowStationaryForMode(String mode){
        if("OFFLINE_NATIVE_ANIMATED_SUBJECT".equals(mode))return true;
        if("OFFLINE_NATIVE_CINEMATIC".equals(mode))return false;
        throw new IllegalArgumentException("explicit supported cinematic mode required");
    }
    public CinematicProgram(double[] p,int fps,int frames){this(p,fps,frames,false);}
    public CinematicProgram(double[] p,int fps,int frames,boolean allowStationary){
        if(p.length!=10||fps<1||fps>60||frames<2||frames>600)throw new IllegalArgumentException("camera/fps/frame bounds");
        this.p=p.clone();this.fps=fps;this.frames=frames;
        this.mode=allowStationary?"OFFLINE_NATIVE_ANIMATED_SUBJECT":"OFFLINE_NATIVE_CINEMATIC";
        for(double v:p)if(!Double.isFinite(v))throw new IllegalArgumentException("nonfinite camera");
        if(Math.abs(p[0])>29999984||Math.abs(p[2])>29999984||Math.abs(p[5])>29999984||Math.abs(p[7])>29999984||p[1]<-64||p[1]>512||p[6]<-64||p[6]>512||Math.abs(p[4])>90||Math.abs(p[9])>90)throw new IllegalArgumentException("camera bounds");
        if(allowStationary){
            for(int i=0;i<5;i++)if(Double.compare(p[i],p[i+5])!=0)throw new IllegalArgumentException("animated subject requires exact fixed camera pose");
        }else{
        if(Math.hypot(Math.hypot(p[5]-p[0],p[7]-p[2]),p[6]-p[1])<0.01)throw new IllegalArgumentException("translating camera required");
        }
    }
    public CinematicFrameState.Pose pose(int index){
        if(index<0||index>=frames)throw new IllegalArgumentException("frame index");
        double k=index/(double)(frames-1),e=k*k*(3-2*k);
        double yawDelta=((p[8]-p[3]+180)%360+360)%360-180;
        return new CinematicFrameState.Pose(p[0]+(p[5]-p[0])*e,p[1]+(p[6]-p[1])*e,p[2]+(p[7]-p[2])*e,(float)(p[3]+yawDelta*e),(float)(p[4]+(p[9]-p[4])*e));
    }
}
