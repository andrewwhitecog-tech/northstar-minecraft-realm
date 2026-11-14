package nsp.walk;
import java.io.OutputStream;
import java.io.Writer;
import java.io.IOException;
import java.util.function.LongSupplier;
import java.util.zip.CRC32;

/** Single writer commits a real framebuffer and its identity together; no frame synthesis. */
public final class CinematicCommitter {
    private CinematicCommitter() {}
    public static void write(CinematicFrameState state,CinematicFrameState.Ticket t,byte[] data,int frameBytes,OutputStream raw,Writer index,LongSupplier clock) throws IOException {
        write(state,t,data,frameBytes,raw,index,clock,"OFFLINE_NATIVE_CINEMATIC");
    }
    public static void write(CinematicFrameState state,CinematicFrameState.Ticket t,byte[] data,int frameBytes,OutputStream raw,Writer index,LongSupplier clock,String mode) throws IOException {
        try {
            if(!"OFFLINE_NATIVE_CINEMATIC".equals(mode)&&!"OFFLINE_NATIVE_ANIMATED_SUBJECT".equals(mode))throw new IOException("explicit supported spool mode required");
            if(data.length!=frameBytes||!state.writable(t))throw new IOException("frame ownership/size mismatch");
            raw.write(data);raw.flush();
            CRC32 crc=new CRC32();crc.update(data);
            var p=t.pose();
            index.write("{\"mode\":\""+mode+"\",\"index\":"+t.index()+",\"renderId\":"+t.renderId()+",\"offset\":"+((long)t.index()*frameBytes)+",\"bytes\":"+frameBytes+",\"crc32\":"+crc.getValue()+",\"pose\":["+p.x()+","+p.y()+","+p.z()+","+p.yaw()+","+p.pitch()+"]}\n");
            index.flush();
            if(!state.committed(t,clock.getAsLong()))throw new IOException("frame not committed: "+state.error());
        } catch(IOException|RuntimeException e){state.fail("write/index failure: "+e);throw e;}
    }
}
