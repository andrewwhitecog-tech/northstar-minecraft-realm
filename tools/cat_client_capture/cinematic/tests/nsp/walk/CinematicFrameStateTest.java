package nsp.walk;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import java.io.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicLong;

final class CinematicFrameStateTest {
    private static final CinematicFrameState.Pose P=new CinematicFrameState.Pose(1,2,3,4,5);
    private CinematicFrameState state(){return new CinematicFrameState(2,0,1000,100);}
    @Test void delayedGpuDoesNotAdvanceOrAdmitSecondRender(){
        var s=state();var t=s.begin(1,P,true,1);assertTrue(s.rendered(t,P,2));
        assertNull(s.begin(2,P,true,50));assertEquals(0,s.index());
        assertTrue(s.copied(t,60));assertEquals(0,s.index());assertTrue(s.committed(t,70));assertEquals(1,s.index());
    }
    @Test void missingRamPreventsSubmission(){var s=state();assertNull(s.begin(1,P,false,1));assertEquals(CinematicFrameState.Phase.FAILED,s.phase());assertEquals(0,s.index());}
    @Test void wrongPoseAndOutOfOrderCallbackFailClosed(){
        var s=state();var t=s.begin(1,P,true,1);assertFalse(s.rendered(t,new CinematicFrameState.Pose(2,2,3,4,5),2));assertNotNull(s.error());
        var s2=state();var t2=s2.begin(1,P,true,1);assertFalse(s2.copied(t2,2));assertEquals(0,s2.index());
    }
    @Test void wrongTicketAndDuplicateCommitAreErrors(){
        var s=state();var t=s.begin(1,P,true,1);s.rendered(t,P,2);assertFalse(s.copied(new CinematicFrameState.Ticket(0,2,P),3));
        var s2=state();var t2=s2.begin(1,P,true,1);s2.rendered(t2,P,2);s2.copied(t2,3);assertTrue(s2.committed(t2,4));assertFalse(s2.committed(t2,5));assertEquals(1,s2.index());
    }
    @Test void frameAndOverallDeadlinesNeverFabricateCommit(){
        var s=state();s.begin(1,P,true,1);s.check(101);assertEquals(CinematicFrameState.Phase.FAILED,s.phase());assertEquals(0,s.index());
        var idle=state();idle.check(1000);assertEquals("overall deadline",idle.error());
    }
    @Test void delayedActualWriteAndIndexFlushHoldCameraIndex() throws Exception {
        var s=state();var t=s.begin(1,P,true,1);s.rendered(t,P,2);s.copied(t,3);
        var rawEntered=new CountDownLatch(1);var releaseRaw=new CountDownLatch(1);var indexEntered=new CountDownLatch(1);var releaseIndex=new CountDownLatch(1);
        OutputStream raw=new OutputStream(){public void write(int b){} public void write(byte[] b)throws IOException{rawEntered.countDown();await(releaseRaw);}};
        Writer idx=new StringWriter(){public void flush(){indexEntered.countDown();try{if(!releaseIndex.await(2,TimeUnit.SECONDS))throw new AssertionError("index test timeout");}catch(InterruptedException e){throw new AssertionError(e);}}};
        var pool=Executors.newSingleThreadExecutor();try{
            var f=pool.submit(()->{CinematicCommitter.write(s,t,new byte[4],4,raw,idx,()->4);return null;});
            assertTrue(rawEntered.await(2,TimeUnit.SECONDS));assertEquals(0,s.index());assertNull(s.begin(2,P,true,4));releaseRaw.countDown();
            assertTrue(indexEntered.await(2,TimeUnit.SECONDS));assertEquals(0,s.index());assertEquals(CinematicFrameState.Phase.WRITE,s.phase());releaseIndex.countDown();f.get(2,TimeUnit.SECONDS);
            assertEquals(1,s.index());assertTrue(idx.toString().contains("\"index\":0"));
        }finally{releaseRaw.countDown();releaseIndex.countDown();pool.shutdownNow();assertTrue(pool.awaitTermination(2,TimeUnit.SECONDS));}
    }
    private static void await(CountDownLatch l)throws IOException{try{if(!l.await(2,TimeUnit.SECONDS))throw new IOException("raw test timeout");}catch(InterruptedException e){Thread.currentThread().interrupt();throw new IOException(e);}}
    @Test void partialRawOrIndexFailureCannotAdvance() {
        for(boolean rawFails:new boolean[]{true,false}){
            var s=state();var t=s.begin(1,P,true,1);s.rendered(t,P,2);s.copied(t,3);
            OutputStream raw=new OutputStream(){public void write(int b)throws IOException{if(rawFails)throw new IOException("actual raw failure");}};
            Writer idx=new Writer(){public void write(char[] b,int o,int n)throws IOException{throw new IOException("actual index failure");}public void flush(){}public void close(){}};
            assertThrows(IOException.class,()->CinematicCommitter.write(s,t,new byte[4],4,raw,idx,()->4));assertEquals(0,s.index());assertEquals(CinematicFrameState.Phase.FAILED,s.phase());
        }
    }
    @Test void finalFrameDrainsExactlyAndRejectsFurtherAdmission() throws Exception {
        var s=state();var raw=new ByteArrayOutputStream();var idx=new StringWriter();
        for(int i=0;i<2;i++){var t=s.begin(i+1,P,true,1+i*4);s.rendered(t,P,2+i*4);s.copied(t,3+i*4);final long now=4+i*4;CinematicCommitter.write(s,t,new byte[4],4,raw,idx,()->now);}
        assertEquals(8,raw.size());assertEquals(2,idx.toString().lines().count());assertEquals(CinematicFrameState.Phase.COMPLETE,s.phase());assertNull(s.begin(3,P,true,10));assertEquals(2,s.index());
    }
    @Test void authoredProgramHasRealTranslationEndpointsAndFiniteBounds(){
        var p=new CinematicProgram(new double[]{0,2,0,170,0,10,4,5,-170,10},24,144);
        assertEquals(0,p.pose(0).x());assertEquals(10,p.pose(143).x());assertTrue(p.pose(72).x()>p.pose(71).x());assertThrows(IllegalArgumentException.class,()->p.pose(144));
        assertThrows(IllegalArgumentException.class,()->new CinematicProgram(new double[]{0,2,0,0,0,0,2,0,10,0},24,144));
        assertThrows(IllegalArgumentException.class,()->new CinematicProgram(new double[]{0,Double.NaN,0,0,0,1,2,0,0,0},24,144));
    }
}
