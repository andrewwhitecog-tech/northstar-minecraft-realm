package net.northstar.gear;
import net.minecraft.server.*;import net.minecraft.server.network.ServerPlayerEntity;import net.minecraft.registry.*;import net.minecraft.world.World;import net.minecraft.util.Identifier;import net.minecraft.util.WorldSavePath;import net.minecraft.util.math.BlockPos;import net.minecraft.block.*;import java.util.*;import java.nio.file.*;import com.google.gson.*;
/** Moving light only occupies air. Persist cleanup ledger before touching world. */
public final class LanternLights {
 record Light(String dimension,int x,int y,int z){}
 static final List<Light> lights=new ArrayList<>();static final Gson GSON=new Gson();
 static Path file(MinecraftServer s){return s.getSavePath(WorldSavePath.ROOT).resolve("northstar_lantern_cleanup.json");}
 public static void recover(MinecraftServer s){try{if(Files.exists(file(s)))lights.addAll(Arrays.asList(GSON.fromJson(Files.readString(file(s)),Light[].class)));clear(s);}catch(Exception e){throw new IllegalStateException("Lantern recovery failed",e);}}
 public static void clear(MinecraftServer s){for(var l:lights){var w=s.getWorld(RegistryKey.of(RegistryKeys.WORLD,Identifier.of(l.dimension)));if(w==null)continue;var p=new BlockPos(l.x,l.y,l.z);w.getChunk(p);var b=w.getBlockState(p);if(b.isOf(Blocks.LIGHT)&&b.get(LightBlock.LEVEL_15)==11)w.setBlockState(p,Blocks.AIR.getDefaultState(),3);}lights.clear();save(s);}
 public static void place(ServerPlayerEntity p){BlockPos b=p.getBlockPos().up();var w=p.getServerWorld();if(!w.getBlockState(b).isAir())return;lights.add(new Light(w.getRegistryKey().getValue().toString(),b.getX(),b.getY(),b.getZ()));save(p.getServer());w.setBlockState(b,Blocks.LIGHT.getDefaultState().with(LightBlock.LEVEL_15,11),3);}
 public static void save(MinecraftServer s){try{Path f=file(s),tmp=f.resolveSibling(f.getFileName()+".tmp");Files.writeString(tmp,GSON.toJson(lights));Files.move(tmp,f,StandardCopyOption.REPLACE_EXISTING,StandardCopyOption.ATOMIC_MOVE);}catch(Exception e){throw new IllegalStateException("Lantern cleanup journal failed",e);}}
}
