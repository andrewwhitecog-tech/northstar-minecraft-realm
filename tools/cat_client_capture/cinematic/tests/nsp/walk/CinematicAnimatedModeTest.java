package nsp.walk;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;
import java.io.ByteArrayOutputStream;
import java.io.StringWriter;
import java.util.zip.CRC32;
final class CinematicAnimatedModeTest {
 private static double[] still(){return new double[]{-2856,106,-1790,-90,0,-2856,106,-1790,-90,0};}
 @Test void originalModeStillRejectsStationary(){
  var e=assertThrows(IllegalArgumentException.class,()->new CinematicProgram(still(),24,600));
  assertEquals("translating camera required",e.getMessage());
  assertFalse(CinematicProgram.allowStationaryForMode("OFFLINE_NATIVE_CINEMATIC"));
 }
 @Test void explicitAnimatedModeAcceptsAll600ExactPoses(){
  boolean allow=CinematicProgram.allowStationaryForMode("OFFLINE_NATIVE_ANIMATED_SUBJECT");
  assertTrue(allow);var p=new CinematicProgram(still(),24,600,allow);
  assertEquals("OFFLINE_NATIVE_ANIMATED_SUBJECT",p.mode);
  for(int i=0;i<600;i++)assertEquals(new CinematicFrameState.Pose(-2856,106,-1790,-90,0),p.pose(i));
  assertThrows(IllegalArgumentException.class,()->p.pose(600));
 }
 @Test void animatedModeRejectsTranslationAndRotation(){
  for(int component=0;component<5;component++){
   double[] p=still();p[component+5]+=.125;
   assertThrows(IllegalArgumentException.class,()->new CinematicProgram(p,24,600,true));
  }
 }
 @Test void onlyExactModeNamesAccepted(){
  for(String s:new String[]{"", "OFFLINE_NATIVE_ANIMATED_SUBJECT ","allowStationary", "offline_native_cinematic"})
   assertThrows(IllegalArgumentException.class,()->CinematicProgram.allowStationaryForMode(s));
  assertThrows(IllegalArgumentException.class,()->CinematicProgram.allowStationaryForMode(null));
 }
 @Test void originalTranslationAndAllInputBoundsRemain(){
  double[] moving=still();moving[5]+=1;var p=new CinematicProgram(moving,24,600);
  assertEquals("OFFLINE_NATIVE_CINEMATIC",p.mode);assertEquals(-2855,p.pose(599).x());
  for(int n:new int[]{0,1,601})assertThrows(IllegalArgumentException.class,()->new CinematicProgram(still(),24,n,true));
  for(int fps:new int[]{0,61})assertThrows(IllegalArgumentException.class,()->new CinematicProgram(still(),fps,600,true));
  assertThrows(IllegalArgumentException.class,()->new CinematicProgram(new double[9],24,600,true));
  double[] bad=still();bad[0]=Double.NaN;assertThrows(IllegalArgumentException.class,()->new CinematicProgram(bad,24,600,true));
  double[] pitch=still();pitch[4]=pitch[9]=91;assertThrows(IllegalArgumentException.class,()->new CinematicProgram(pitch,24,600,true));
 }
 @Test void frameStateStillRejectsChangedPoseAndDuplicateRenderId(){
  var pose=new CinematicFrameState.Pose(1,2,3,0,0);
  var s=new CinematicFrameState(2,0,1000,100);var t=s.begin(7,pose,true,1);
  assertFalse(s.rendered(t,new CinematicFrameState.Pose(2,2,3,0,0),2));
  assertEquals(CinematicFrameState.Phase.FAILED,s.phase());
  var a=new CinematicFrameState(2,0,1000,100);var q=a.begin(7,pose,true,1);
  assertTrue(a.rendered(q,pose,2));assertTrue(a.copied(q,3));assertTrue(a.committed(q,4));
  assertNull(a.begin(7,pose,true,5));assertEquals("render identity order",a.error());
 }
 @Test void realCommitBytesCrcAndActualModeTravelTogether() throws Exception {
  var pose=new CinematicFrameState.Pose(1,2,3,0,0);var state=new CinematicFrameState(2,0,1000,100);
  var raw=new ByteArrayOutputStream();var index=new StringWriter();byte[] data={1,7,19,31};
  for(int i=0;i<2;i++){
   var ticket=state.begin(100+i,pose,true,1+i*4);assertTrue(state.rendered(ticket,pose,2+i*4));assertTrue(state.copied(ticket,3+i*4));
   final long now=4+i*4;CinematicCommitter.write(state,ticket,data,4,raw,index,()->now,"OFFLINE_NATIVE_ANIMATED_SUBJECT");
  }
  assertEquals(CinematicFrameState.Phase.COMPLETE,state.phase());assertArrayEquals(new byte[]{1,7,19,31,1,7,19,31},raw.toByteArray());
  var crc=new CRC32();crc.update(data);String[] rows=index.toString().split("\n");assertEquals(2,rows.length);
  for(int i=0;i<2;i++){
   assertTrue(rows[i].contains("\"mode\":\"OFFLINE_NATIVE_ANIMATED_SUBJECT\""));
   assertTrue(rows[i].contains("\"renderId\":"+(100+i)));assertTrue(rows[i].contains("\"crc32\":"+crc.getValue()));
  }
 }
}
