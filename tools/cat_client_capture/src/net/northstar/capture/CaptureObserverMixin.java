package net.northstar.capture;
import java.nio.file.*;
import java.time.Instant;
import java.util.*;
import com.google.gson.Gson;
import net.minecraft.client.Minecraft;
import net.minecraft.world.entity.animal.feline.Cat;
import org.spongepowered.asm.mixin.Mixin;
import org.spongepowered.asm.mixin.Unique;
import org.spongepowered.asm.mixin.injection.At;
import org.spongepowered.asm.mixin.injection.Inject;
import org.spongepowered.asm.mixin.injection.callback.CallbackInfo;
/** Observes the real client; no entity movement, damage, rendering or AI substitution. */
@Mixin(Minecraft.class)
public abstract class CaptureObserverMixin {
 @Unique private long nsp$frames;
 @Unique private boolean nsp$stopping;
 @Inject(method="renderFrame(Z)V",at=@At("TAIL"),remap=false)
 private void nsp$observe(boolean rendering,CallbackInfo ci) {
  if(nsp$stopping)return;
  String dir=System.getProperty("nsp.cat.capture.dir");if(dir==null)return;
  Minecraft m=(Minecraft)(Object)this;Path root=Path.of(dir);nsp$frames++;
  try {
   boolean stop=Files.exists(root.resolve("STOP_CLIENT"));
   if(nsp$frames%20!=0&&!stop)return;
   Map<String,Object> state=new LinkedHashMap<>();state.put("utc",Instant.now().toString());state.put("renderFrameCalls",nsp$frames);state.put("joined",m.player!=null&&m.level!=null);state.put("stopRequested",stop);
   if(m.player!=null&&m.level!=null){state.put("player",m.player.getName().getString());state.put("position",List.of(m.player.getX(),m.player.getY(),m.player.getZ()));state.put("spectator",m.player.isSpectator());state.put("hudHidden",m.gui.hud.isHidden());List<Object> cats=new ArrayList<>();for(Cat c:m.level.getEntitiesOfClass(Cat.class,m.player.getBoundingBox().inflate(48))){cats.add(Map.of("id",c.getId(),"position",List.of(c.getX(),c.getY(),c.getZ()),"alive",c.isAlive()));}state.put("clientCats",cats);}
   Path tmp=root.resolve("CLIENT_ACTUAL.json.tmp");Files.writeString(tmp,new Gson().toJson(state));Files.move(tmp,root.resolve("CLIENT_ACTUAL.json"),StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);
   if(stop){nsp$stopping=true;m.stop();}
  }catch(Exception e){nsp$stopping=true;try{Files.writeString(root.resolve("CLIENT_ERROR.txt"),e.toString());}catch(Exception ignored){}m.stop();}
 }
}
