package nsp.walk;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.LinkOption;
import java.io.IOException;
/** Fresh per-take destinations only; never remove/reuse an earlier raw frame or receipt. */
final class CinematicTakePaths {
    record Take(Path base,Path receipt) {}
    static Take create(Path route,String name)throws IOException {
        if(name==null||!name.matches("[a-z0-9_]{1,48}"))throw new IOException("relative take allowlist");
        Path parent=route.resolve("cinematic_spool");
        if(!Files.exists(parent,LinkOption.NOFOLLOW_LINKS))Files.createDirectory(parent);
        if(Files.isSymbolicLink(parent)||!Files.isDirectory(parent,LinkOption.NOFOLLOW_LINKS)||!parent.toRealPath().equals(parent.toAbsolutePath().normalize()))throw new IOException("owned spool directory required");
        Path take=parent.resolve(name);Files.createDirectory(take);
        return new Take(take.resolve(name),take.resolve("writer.json"));
    }
}
