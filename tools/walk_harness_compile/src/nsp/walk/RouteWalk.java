package nsp.walk;

import com.google.gson.Gson;
import com.google.gson.GsonBuilder;
import com.google.gson.JsonArray;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import net.minecraft.client.Minecraft;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.entity.Interaction;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.BlockHitResult;
import net.minecraft.world.phys.EntityHitResult;
import net.minecraft.world.phys.Vec3;

/**
 * Walks a route and presses buttons on the real client, using key mapping and the game's own interaction, so the server sees a real walk and a real press. No OS input, and it
 * never reads the session. Waits for steps.json in the folder named by nsp.walk.dir, runs it, writes walk_log.json after every step, and reports where it stuck.
 * Steps: {"walk":[x,z]}, {"press":[x,y,z],"face":"NORTH"}, {"wait":ticks}, {"mark":"text"}, {"slot":n}, {"cmd":"trigger x set 1"}.
 * Filming: {"rec":"name","fps":30} starts recording the game's own framebuffer, {"recstop":true} ends it and waits for ffmpeg, {"cam":[x,y,z,yaw,pitch, x,y,z,yaw,pitch],"seconds":8} moves a spectator
 * from the first pose to the second, set on every rendered frame so the shot stays smooth. ffmpeg's arguments come from ffmpeg_args.txt in the same folder, with {NAME} for the take.
 */
public final class RouteWalk implements ClientModInitializer {
    private static volatile FrameRecorder recorder;
    private static volatile double[] cam;
    private static volatile long camStart, camNanos;
    private static volatile boolean camDone;
    private final Path dir = Path.of(System.getProperty("nsp.walk.dir", "nsp_walk"));
    private final Gson gson = new GsonBuilder().setPrettyPrinting().create();
    private final List<Map<String, Object>> rows = new ArrayList<>();
    private JsonArray steps;
    private int step, stepTicks, stuckCount, total;
    private float turnYaw, turnPitch;
    private double lastDist = 1e9;
    private boolean done;

    @Override
    public void onInitializeClient() {
        ClientTickEvents.END_CLIENT_TICK.register(c -> {
            try {
                tick(c);
            } catch (Throwable e) {
                row(c, "ERROR", e.toString());
                done = true;
            }
        });
    }

    /** Called by the mixin on every rendered frame: keeps the finished frame, then sets the camera for the next one. */
    public static void onFrame(Minecraft c) {
        FrameRecorder r = recorder;
        if (r != null) r.onFrame(c.gameRenderer.mainRenderTarget());
        double[] p = cam;
        if (p == null || c.player == null) return;
        double k = Math.min(1.0, (System.nanoTime() - camStart) / (double) camNanos);
        double e = k * k * (3 - 2 * k);
        double yaw = p[3] + net.minecraft.util.Mth.wrapDegrees(p[8] - p[3]) * e;
        double pitch = p[4] + (p[9] - p[4]) * e;
        c.player.setPos(p[0] + (p[5] - p[0]) * e, p[1] + (p[6] - p[1]) * e, p[2] + (p[7] - p[2]) * e);
        c.player.setYRot((float) yaw);
        c.player.setXRot((float) pitch);
        c.player.setDeltaMovement(Vec3.ZERO);
        c.player.setOldPosAndRot();
        if (k >= 1.0) {
            cam = null;
            camDone = true;
        }
    }

    private void row(Minecraft c, String what, Object value) {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("utc", java.time.Instant.now().toString());
        m.put("step", step);
        m.put("what", what);
        m.put("value", value);
        if (c.player != null) {
            m.put("pos", List.of(c.player.getX(), c.player.getY(), c.player.getZ()));
            m.put("onGround", c.player.onGround());
        }
        rows.add(m);
        try {
            Files.writeString(dir.resolve("walk_log.json"), gson.toJson(rows));
        } catch (Exception ignore) {
        }
    }

    private void next(Minecraft c) {
        c.options.keyUp.setDown(false);
        step++;
        stepTicks = 0;
        stuckCount = 0;
        lastDist = 1e9;
    }

    /** Ready for the next steps.json, so a stop doesn't need a client restart. */
    private void reset(Minecraft c) {
        c.options.keyUp.setDown(false);
        steps = null;
        step = 0;
        stepTicks = 0;
        stuckCount = 0;
        lastDist = 1e9;
    }

    private void tick(Minecraft c) throws Exception {
        if (c.player == null || c.level == null || done) return;
        total++;
        if (steps == null) {
            Path p = dir.resolve("steps.json");
            if (total % 20 == 0 && Files.exists(p)) {
                steps = JsonParser.parseString(Files.readString(p)).getAsJsonArray();
                Files.move(p, dir.resolve("steps_running.json"), java.nio.file.StandardCopyOption.REPLACE_EXISTING);
                row(c, "START", steps.size());
            }
            return;
        }
        if (step >= steps.size()) {
            row(c, "DONE", total);
            reset(c);
            return;
        }
        JsonObject s = steps.get(step).getAsJsonObject();
        stepTicks++;
        if (s.has("mark")) {
            row(c, "MARK", s.get("mark").getAsString());
            next(c);
        } else if (s.has("cmd")) {
            c.getConnection().sendCommand(s.get("cmd").getAsString());
            row(c, "CMD", s.get("cmd").getAsString());
            next(c);
        } else if (s.has("slot")) {
            c.player.getInventory().setSelectedSlot(s.get("slot").getAsInt());
            row(c, "SLOT", s.get("slot").getAsInt());
            next(c);
        } else if (s.has("wait")) {
            if (stepTicks >= s.get("wait").getAsInt()) next(c);
        } else if (s.has("rec")) {
            String name = s.get("rec").getAsString();
            int fps = s.has("fps") ? s.get("fps").getAsInt() : 30;
            Path args = dir.resolve("args_" + name + ".txt");
            Files.writeString(args, Files.readString(dir.resolve("ffmpeg_args.txt")).replace("{NAME}", name));
            recorder = new FrameRecorder(c.gameRenderer.mainRenderTarget(), fps, args, dir.resolve("ffmpeg_" + name + ".log"));
            row(c, "REC", name);
            next(c);
        } else if (s.has("recstop")) {
            FrameRecorder r = recorder;
            if (r == null) {
                row(c, "RECSTOP", "nothing recording");
                next(c);
            } else {
                if (stepTicks == 1) r.requestStop();
                if (r.isClosed() || stepTicks > 800) {
                    row(c, "RECSTOP", r.stats());
                    recorder = null;
                    next(c);
                }
            }
        } else if (s.has("cam")) {
            if (stepTicks == 1) {
                JsonArray t = s.getAsJsonArray("cam");
                double[] p = new double[10];
                for (int i = 0; i < 10; i++) p[i] = t.get(i).getAsDouble();
                camNanos = (long) (s.get("seconds").getAsDouble() * 1e9);
                camStart = System.nanoTime();
                camDone = false;
                cam = p;
                row(c, "CAM", t.toString());
            }
            if (camDone) next(c);
        } else if (s.has("walk")) {
            JsonArray t = s.getAsJsonArray("walk");
            double dx = t.get(0).getAsDouble() - c.player.getX(), dz = t.get(1).getAsDouble() - c.player.getZ(), d = Math.hypot(dx, dz);
            if (d < 0.4) {
                row(c, "REACHED", t.toString());
                next(c);
                return;
            }
            c.player.setYRot((float) Math.toDegrees(Math.atan2(-dx, dz)));
            c.player.setXRot(0);
            c.options.keyUp.setDown(true);
            if (stepTicks % 40 == 0) {
                stuckCount = lastDist - d < 0.3 ? stuckCount + 1 : 0;
                lastDist = d;
                if (stuckCount >= 3) {
                    c.options.keyUp.setDown(false);
                    row(c, "STUCK", t.toString());
                    reset(c);
                }
            }
        } else if (s.has("press")) {
            JsonArray t = s.getAsJsonArray("press");
            BlockPos p = new BlockPos(t.get(0).getAsInt(), t.get(1).getAsInt(), t.get(2).getAsInt());
            Direction f = Direction.valueOf(s.get("face").getAsString());
            Vec3 at = Vec3.atCenterOf(p);
            double dx = at.x - c.player.getX(), dy = at.y - c.player.getEyeY(), dz = at.z - c.player.getZ();
            c.player.setYRot((float) Math.toDegrees(Math.atan2(-dx, dz)));
            c.player.setXRot((float) -Math.toDegrees(Math.atan2(dy, Math.hypot(dx, dz))));
            if (stepTicks >= 4) {
                var r = c.gameMode.useItemOn(c.player, InteractionHand.MAIN_HAND, new BlockHitResult(at, f, p, false));
                row(c, "PRESS", p.toShortString() + " " + r);
                next(c);
            }
        } else if (s.has("click")) {
            c.gameMode.handleContainerInput(c.player.containerMenu.containerId, s.get("click").getAsInt(), 0, net.minecraft.world.inventory.ContainerInput.PICKUP, c.player);
            row(c, "CLICK", s.get("click").getAsInt() + " in " + c.player.containerMenu.getClass().getSimpleName());
            next(c);
        } else if (s.has("close")) {
            c.player.closeContainer();
            row(c, "CLOSE", "menu closed");
            next(c);
        } else if (s.has("menu")) {
            row(c, "MENU", c.player.containerMenu.getClass().getSimpleName());
            next(c);
        } else if (s.has("use")) {
            var r = c.gameMode.useItem(c.player, InteractionHand.MAIN_HAND);
            row(c, "USE", String.valueOf(r));
            next(c);
        } else if (s.has("await")) {
            // The external judge acknowledges a run-specific mark only after its authoritative reads.
            String a = s.get("await").getAsString();
            int max = s.has("ticks") ? s.get("ticks").getAsInt() : 2400;
            if (Files.exists(dir.resolve("ack_" + a))) {
                row(c, "ACK", a + " after " + stepTicks + " ticks");
                next(c);
            } else if (stepTicks >= max) {
                // Match the existing ERROR terminal lifecycle: no later step or replacement route can run.
                done = true;
                c.options.keyUp.setDown(false);
                row(c, "AWAIT_TIMEOUT", a);
                c.gameMode.stopDestroyBlock();
            }
        } else if (s.has("dighold")) {
            // Hard-block survival proof: sustain mining; one start alone may only begin damage.
            // Instant-break exceptions still exist. Old "dig" semantics are deliberately unchanged.
            // DIGHOLD reports the client only; the judge must read the authoritative server state.
            boolean holdPending = false;
            try {
                JsonArray t = s.getAsJsonArray("dighold");
                BlockPos p = new BlockPos(t.get(0).getAsInt(), t.get(1).getAsInt(), t.get(2).getAsInt());
                Direction f = Direction.valueOf(s.get("face").getAsString());
                int max = s.has("ticks") ? s.get("ticks").getAsInt() : 160;
                Vec3 at = Vec3.atCenterOf(p);
                double dx = at.x - c.player.getX(), dy = at.y - c.player.getEyeY(), dz = at.z - c.player.getZ();
                c.player.setYRot((float) Math.toDegrees(Math.atan2(-dx, dz)));
                c.player.setXRot((float) -Math.toDegrees(Math.atan2(dy, Math.hypot(dx, dz))));
                if (stepTicks == 2) {
                    row(c, "DIGSTART", p.toShortString() + " " + c.gameMode.startDestroyBlock(p, f) + " " + c.level.getBlockState(p));
                } else if (stepTicks > 2) {
                    c.gameMode.continueDestroyBlock(p, f);
                    boolean air = c.level.getBlockState(p).isAir();
                    if (air || stepTicks >= max) {
                        row(c, "DIGHOLD", p.toShortString() + " ticks " + stepTicks + " client_sees " + c.level.getBlockState(p));
                        next(c);
                        return;
                    }
                }
                holdPending = true;
            } finally {
                // Runs on completion, predicted air, deadline, or any thrown failure; never retarget a neighbor.
                if (!holdPending) {
                    c.options.keyUp.setDown(false);
                    c.gameMode.stopDestroyBlock();
                }
            }
        } else if (s.has("dig")) {
            JsonArray t = s.getAsJsonArray("dig");
            BlockPos p = new BlockPos(t.get(0).getAsInt(), t.get(1).getAsInt(), t.get(2).getAsInt());
            row(c, "DIG", p.toShortString() + " " + c.gameMode.startDestroyBlock(p, Direction.valueOf(s.get("face").getAsString())));
            next(c);
        } else if (s.has("clouds")) {
            c.options.cloudStatus().set(s.get("clouds").getAsBoolean() ? net.minecraft.client.CloudStatus.FANCY : net.minecraft.client.CloudStatus.OFF);
            row(c, "CLOUDS", String.valueOf(c.options.cloudStatus().get()));
            next(c);
        } else if (s.has("gamma")) {
            c.options.gamma().set(s.get("gamma").getAsDouble());
            row(c, "GAMMA", String.valueOf(c.options.gamma().get()));
            next(c);
        } else if (s.has("turn")) {
            JsonArray t = s.getAsJsonArray("turn");
            if (stepTicks == 1) { turnYaw = c.player.getYRot(); turnPitch = c.player.getXRot(); }
            float k = Math.min(1f, stepTicks / t.get(2).getAsFloat());
            c.player.setYRot(turnYaw + net.minecraft.util.Mth.wrapDegrees(t.get(0).getAsFloat() - turnYaw) * k);
            c.player.setXRot(turnPitch + (t.get(1).getAsFloat() - turnPitch) * k);
            if (k >= 1f) { row(c, "TURN", c.player.getYRot() + " " + c.player.getXRot()); next(c); }
        } else if (s.has("foveffect")) {
            c.options.fovEffectScale().set(s.get("foveffect").getAsDouble());
            row(c, "FOVEFFECT", String.valueOf(c.options.fovEffectScale().get()));
            next(c);
        } else if (s.has("hud")) {
            if (c.gui.hud.isHidden() == s.get("hud").getAsBoolean()) c.gui.hud.toggle();
            row(c, "HUD", "hidden " + c.gui.hud.isHidden());
            next(c);
        } else if (s.has("shot")) {
            net.minecraft.client.Screenshot.grab(c.gameDirectory, s.get("shot").getAsString() + ".png", c.gameRenderer.mainRenderTarget(), 1, m -> {});
            row(c, "SHOT", s.get("shot").getAsString());
            next(c);
        } else if (s.has("particles")) {
            c.options.particles().set(net.minecraft.server.level.ParticleStatus.values()[s.get("particles").getAsInt()]);
            row(c, "PARTICLES", String.valueOf(c.options.particles().get()));
            next(c);
        } else if (s.has("interact")) {
            JsonArray t = s.getAsJsonArray("interact");
            Vec3 at = new Vec3(t.get(0).getAsDouble(), t.get(1).getAsDouble(), t.get(2).getAsDouble());
            net.minecraft.world.entity.Entity e = c.level.getEntitiesOfClass(net.minecraft.world.entity.Entity.class, new AABB(at, at).inflate(1.5), x -> x != c.player && (x instanceof Interaction || x instanceof net.minecraft.world.entity.LivingEntity)).stream()
                    .min(java.util.Comparator.comparingDouble(x -> x.distanceToSqr(at))).orElse(null);
            if (e == null) {
                row(c, "INTERACT", "no entity at " + at);
                next(c);
            } else {
                Vec3 mid = e.getBoundingBox().getCenter();
                double dx = mid.x - c.player.getX(), dy = mid.y - c.player.getEyeY(), dz = mid.z - c.player.getZ();
                c.player.setYRot((float) Math.toDegrees(Math.atan2(-dx, dz)));
                c.player.setXRot((float) -Math.toDegrees(Math.atan2(dy, Math.hypot(dx, dz))));
                if (stepTicks >= 4) {
                    var r = c.gameMode.interact(c.player, e, new EntityHitResult(e, mid), InteractionHand.MAIN_HAND);
                    row(c, "INTERACT", e.getId() + " " + r);
                    next(c);
                }
            }
        }
    }
}
