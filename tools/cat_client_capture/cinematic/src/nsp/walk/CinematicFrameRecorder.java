package nsp.walk;
import com.mojang.blaze3d.pipeline.RenderTarget;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.renderpearl.api.buffers.GpuBuffer;
import com.mojang.renderpearl.api.buffers.GpuBufferSlice;
import java.io.OutputStream;
import java.io.BufferedOutputStream;
import java.io.BufferedWriter;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardOpenOption;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import net.minecraft.client.Minecraft;
import net.minecraft.world.phys.Vec3;

/** OFFLINE_NATIVE_CINEMATIC. Does not promise real-time gameplay cadence or freeze server time. */
final class CinematicFrameRecorder {
    private final CinematicProgram program;
    private final CinematicFrameState state;
    private final int bytes;
    private final GpuBuffer gpu;
    private final byte[] ram;
    private final AtomicBoolean callbackPending=new AtomicBoolean();
    private final ArrayBlockingQueue<CinematicFrameState.Ticket> ready=new ArrayBlockingQueue<>(1);
    private final OutputStream raw;
    private final BufferedWriter index;
    private final Path receipt;
    private final Thread writer;
    private volatile boolean writerClosed,gpuClosed;
    private volatile CinematicFrameState.Ticket renderTicket;
    private long renderId,submitted,copied;
    private final long started=System.nanoTime();
    CinematicFrameRecorder(CinematicProgram program,Path base,Path receipt) throws Exception {
        this.program=program;this.receipt=receipt;this.bytes=1280*720*4;
        state=new CinematicFrameState(program.frames,started,TimeUnit.SECONDS.toNanos(600),TimeUnit.SECONDS.toNanos(30));
        // All RAM exists before any GPU submission; only one frame may own it.
        ram=new byte[bytes];
        OutputStream openedRaw=new BufferedOutputStream(Files.newOutputStream(base.resolveSibling(base.getFileName()+".rgba"),StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE));
        BufferedWriter openedIndex;
        try { openedIndex=Files.newBufferedWriter(base.resolveSibling(base.getFileName()+".frames.jsonl"),StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE); }
        catch(Exception e){openedRaw.close();throw e;}
        GpuBuffer openedGpu;
        try{openedGpu=RenderSystem.getDevice().createBuffer(()->"nsp offline cinematic frame",9,bytes);}
        catch(Throwable e){openedRaw.close();openedIndex.close();throw e;}
        raw=openedRaw;index=openedIndex;gpu=openedGpu;
        writer=new Thread(this::writeLoop,"nsp-offline-cinematic-writer");writer.setDaemon(true);writer.setPriority(Thread.NORM_PRIORITY-1);writer.start();
    }
    private static CinematicFrameState.Pose actual(Minecraft c){return new CinematicFrameState.Pose(c.player.getX(),c.player.getY(),c.player.getZ(),c.player.getYRot(),c.player.getXRot());}
    void beforeFrame(Minecraft c){ synchronized(state) {
        renderId++;renderTicket=null;state.check(System.nanoTime());disposeIfDrained();
        if(state.phase()==CinematicFrameState.Phase.COMPLETE||state.phase()==CinematicFrameState.Phase.FAILED)return;
        if(c.player==null||c.level==null){state.fail("world/player lost");return;}
        // Keep the pending authored pose while its asynchronous copy/write is outstanding.
        var p=program.pose(state.index());
        c.player.setPos(p.x(),p.y(),p.z());c.player.setYRot(p.yaw());c.player.setXRot(p.pitch());
        c.player.setDeltaMovement(Vec3.ZERO);c.player.setOldPosAndRot();
        if(state.phase()!=CinematicFrameState.Phase.READY||callbackPending.get())return;
        renderTicket=state.begin(renderId,p,true,System.nanoTime());
    }}
    void afterFrame(Minecraft c){
        var t=renderTicket;renderTicket=null;state.check(System.nanoTime());
        if(t!=null){
            if(c.player==null||c.level==null){state.fail("world/player lost before capture");return;}
            RenderTarget target=c.gameRenderer.mainRenderTarget();
            var tex=target.getColorTexture();
            if(tex==null||target.width!=1280||target.height!=720||tex.getFormat().blockSize()!=4){state.fail("exact 1280x720 RGBA framebuffer required");return;}
            if(!state.rendered(t,actual(c),System.nanoTime())){return;}
            callbackPending.set(true);submitted++;
            try{RenderSystem.getDevice().createCommandEncoder().copyTextureToBuffer(tex,gpu,0L,()->onCopied(t),0);}
            catch(Throwable e){callbackPending.set(false);state.fail("GPU submission: "+e);}
        }
        disposeIfDrained();
    }
    private void onCopied(CinematicFrameState.Ticket t){
        try{

            if(!state.copied(t,System.nanoTime())){return;}
            try(GpuBufferSlice.MappedView view=gpu.map(true,false)){view.data().get(0,ram);}
            copied++;
            if(!ready.offer(t))throw new IllegalStateException("single-frame queue overflow");
        }catch(Throwable e){state.fail("GPU callback: "+e);}
        finally{callbackPending.set(false);}
    }
    private void writeLoop(){
        try{
            while(true){
                var t=ready.poll(100,TimeUnit.MILLISECONDS);
                if(t!=null){
                    // The pending state owns RAM until the final commit publishes READY.
                    CinematicCommitter.write(state,t,ram,bytes,raw,index,System::nanoTime,program.mode);
                }
                state.check(System.nanoTime());
                if((state.phase()==CinematicFrameState.Phase.COMPLETE||state.phase()==CinematicFrameState.Phase.FAILED)&&!callbackPending.get()&&ready.isEmpty())break;
            }
        }catch(Throwable e){state.fail("writer: "+e);}
        finally{
            try{raw.close();}catch(Exception e){state.fail("raw close: "+e);}
            try{index.close();}catch(Exception e){state.fail("index close: "+e);}
            writerClosed=true;
            try{Files.writeString(receipt,new com.google.gson.GsonBuilder().setPrettyPrinting().create().toJson(stats()),StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);}
            catch(Exception e){state.fail("receipt: "+e);}
        }
    }
    private void disposeIfDrained(){if(writerClosed&&!callbackPending.get()&&!gpuClosed){try{gpu.close();gpuClosed=true;}catch(Throwable e){state.fail("GPU close: "+e);}}}
    boolean isClosed(){return writerClosed&&gpuClosed;}
    String error(){return state.error();}
    void fail(String why){state.fail(why);}
    Map<String,Object> stats(){var m=new LinkedHashMap<String,Object>();m.put("mode",program.mode);m.put("fps",program.fps);m.put("expectedFrames",program.frames);m.put("framesCommitted",state.index());m.put("framesSubmitted",submitted);m.put("framesCopied",copied);m.put("phase",state.phase().toString());m.put("error",state.error());m.put("writerClosed",writerClosed);m.put("gpuClosed",gpuClosed);m.put("callbackPending",callbackPending.get());m.put("ramReserved",state.phase()==CinematicFrameState.Phase.RENDER||state.phase()==CinematicFrameState.Phase.GPU||state.phase()==CinematicFrameState.Phase.WRITE);m.put("wallSeconds",(System.nanoTime()-started)/1e9);m.put("width",1280);m.put("height",720);m.put("humanInputProof",false);m.put("realTimeGameplayFpsProof",false);return m;}
}
