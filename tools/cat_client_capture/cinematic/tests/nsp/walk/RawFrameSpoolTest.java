package nsp.walk;
import org.junit.jupiter.api.*;import org.junit.jupiter.api.io.TempDir;import java.nio.file.*;import java.io.*;import java.util.*;import static org.junit.jupiter.api.Assertions.*;
/** Real local file/identity unit tests, not GPU/native capture proof. */
class RawFrameSpoolTest{
 @TempDir Path temp;
 @Test void writesRealBytesAndIndexWithoutEncoder()throws Exception{Path base=temp.resolve("take");RawFrameSpool s=new RawFrameSpool(base,4,2);s.output().write(new byte[]{1,2,3,4});s.recordFrame(1,0,4);s.output().write(new byte[]{5,6,7,8});s.recordFrame(2,1,4);s.close();assertArrayEquals(new byte[]{1,2,3,4,5,6,7,8},Files.readAllBytes(s.rawPath));assertEquals(2,Files.readAllLines(s.indexPath).size());assertEquals(8L,s.stats().get("writtenBytes"));assertEquals(true,s.stats().get("closed"));}
 @Test void capacityRefusalDoesNotWriteExtraBytes()throws Exception{RawFrameSpool s=new RawFrameSpool(temp.resolve("bounded"),4,1);s.output().write(new byte[4]);s.recordFrame(1,0,4);assertThrows(IOException.class,()->s.output().write(new byte[4]));s.close();assertEquals(4,Files.size(s.rawPath));}
 @Test void oldSpoolIsNeverOverwritten()throws Exception{Path base=temp.resolve("existing");RawFrameSpool s=new RawFrameSpool(base,4,1);s.output().write(new byte[]{9,8,7,6});s.recordFrame(1,0,4);s.close();assertThrows(FileAlreadyExistsException.class,()->new RawFrameSpool(base,4,1));assertArrayEquals(new byte[]{9,8,7,6},Files.readAllBytes(s.rawPath));}
 @Test void missingIndexCannotBecomeSuccessfulClose()throws Exception{RawFrameSpool s=new RawFrameSpool(temp.resolve("unindexed"),4,1);s.output().write(new byte[4]);assertThrows(IOException.class,s::close);}
}
