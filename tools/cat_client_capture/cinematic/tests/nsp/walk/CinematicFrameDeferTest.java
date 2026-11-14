package nsp.walk;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
/** Pure state transitions; no game, GPU or claimed native proof. */
final class CinematicFrameDeferTest {
 private static final CinematicFrameState.Pose P=new CinematicFrameState.Pose(1,2,3,4,5);
 private CinematicFrameState fresh(){return new CinematicFrameState(2,0,1000,100);}
 @Test void deferKeepsIndexRequiresNewRenderAndThenCommits(){
  var s=fresh();var t=s.begin(8,P,true,1);assertTrue(s.deferRender(t,2));
  assertEquals(0,s.index());assertEquals(CinematicFrameState.Phase.READY,s.phase());
  var next=s.begin(9,P,true,3);assertEquals(0,next.index());assertTrue(s.rendered(next,P,4));assertTrue(s.copied(next,5));assertTrue(s.committed(next,6));assertEquals(1,s.index());
 }
 @Test void deferredIdCannotBeUsedAgain(){var s=fresh();var t=s.begin(8,P,true,1);assertTrue(s.deferRender(t,2));assertNull(s.begin(8,P,true,3));assertEquals("render identity order",s.error());}
 @Test void oldTicketCannotCaptureLaterRetry(){var s=fresh();var old=s.begin(8,P,true,1);assertTrue(s.deferRender(old,2));s.begin(9,P,true,3);assertFalse(s.rendered(old,P,4));assertEquals(CinematicFrameState.Phase.FAILED,s.phase());}
 @Test void wrongAndNullTicketFailClosed(){for(boolean nul:new boolean[]{false,true}){var s=fresh();var t=s.begin(8,P,true,1);assertFalse(s.deferRender(nul?null:new CinematicFrameState.Ticket(0,9,P),2));assertEquals(CinematicFrameState.Phase.FAILED,s.phase());}}
 @Test void noReadyGpuOrWriteDeferral(){
  var ready=fresh();assertFalse(ready.deferRender(null,1));
  for(boolean written:new boolean[]{false,true}){var s=fresh();var t=s.begin(8,P,true,1);assertTrue(s.rendered(t,P,2));if(written)assertTrue(s.copied(t,3));assertFalse(s.deferRender(t,4));assertEquals(CinematicFrameState.Phase.FAILED,s.phase());}
 }
 @Test void pendingTimeoutCannotBeDeflected(){var s=fresh();var t=s.begin(8,P,true,1);assertFalse(s.deferRender(t,101));assertEquals("pending frame deadline",s.error());}
 @Test void globalDeadlineSurvivesRepeatedDeferrals(){var s=new CinematicFrameState(2,0,10,5);for(int i=1;i<5;i++){var t=s.begin(i,P,true,2*i-1);assertTrue(s.deferRender(t,2*i));}var t=s.begin(5,P,true,9);assertFalse(s.deferRender(t,10));assertEquals("overall deadline",s.error());}
 @Test void retryStillNeedsRam(){var s=fresh();var t=s.begin(8,P,true,1);assertTrue(s.deferRender(t,2));assertNull(s.begin(9,P,false,3));assertEquals(CinematicFrameState.Phase.FAILED,s.phase());}
}
