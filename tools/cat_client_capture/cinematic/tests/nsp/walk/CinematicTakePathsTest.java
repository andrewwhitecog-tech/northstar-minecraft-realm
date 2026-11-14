package nsp.walk;
import java.nio.file.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import static org.junit.jupiter.api.Assertions.*;
final class CinematicTakePathsTest {
 @TempDir Path route;
 @Test void successiveTakesHaveDisjointActualFiles()throws Exception{var a=CinematicTakePaths.create(route,"hall_eye");var b=CinematicTakePaths.create(route,"aerial");Files.writeString(a.receipt(),"actual first receipt",StandardOpenOption.CREATE_NEW);Files.writeString(b.receipt(),"actual second receipt",StandardOpenOption.CREATE_NEW);assertNotEquals(a.base().getParent(),b.base().getParent());assertEquals("actual first receipt",Files.readString(a.receipt()));}
 @Test void duplicateNameRefusesWithoutChangingEarlierEvidence()throws Exception{var a=CinematicTakePaths.create(route,"hall_eye");Files.writeString(a.receipt(),"preserve",StandardOpenOption.CREATE_NEW);assertThrows(FileAlreadyExistsException.class,()->CinematicTakePaths.create(route,"hall_eye"));assertEquals("preserve",Files.readString(a.receipt()));}
 @Test void traversalAbsoluteAndInvalidNamesRefuse()throws Exception{for(String name:new String[]{"../escape","/absolute","C:/outside","A","x/y",""})assertThrows(java.io.IOException.class,()->CinematicTakePaths.create(route,name));assertFalse(Files.exists(route.resolve("cinematic_spool")));}
}
