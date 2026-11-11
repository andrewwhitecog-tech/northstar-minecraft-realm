package nsp.walk;

import com.mojang.blaze3d.pipeline.RenderTarget;
import com.mojang.blaze3d.systems.RenderSystem;
import com.mojang.renderpearl.api.buffers.GpuBuffer;
import com.mojang.renderpearl.api.buffers.GpuBufferSlice;
import com.mojang.renderpearl.api.textures.GpuTexture;

import java.io.File;
import java.io.IOException;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ArrayBlockingQueue;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicIntegerArray;
import java.util.concurrent.atomic.AtomicLong;

/**
 * Copies the game's own framebuffer to raw RGBA frames and pipes them to ffmpeg's stdin.
 * Nothing here touches the desktop, so a hidden window records fine and Andrew's screen can never leak in.
 *
 * Render thread: picks frames on a fixed 1/fps clock and asks the GPU to copy them into a small ring of read buffers.
 * Writer thread: feeds ffmpeg, repeating a frame when the game ran slower than the clock, so clip time stays real time.
 * Both ends are bounded. If anything lags, frames are dropped and counted; the game never stalls waiting for the disk.
 */
final class FrameRecorder {
    private static final int GPU_SLOTS = 4;
    private static final int RAM_SLOTS = 6;
    private static final int USAGE_MAP_READ_COPY_DST = 9; // the usage flags Mojang's Screenshot class passes

    private record Frame(byte[] data, long index) {}

    private final int width;
    private final int height;
    private final int fps;
    private final long maxRepeat;
    private final Process ffmpeg;
    private final OutputStream sink;
    private final Thread writer;
    private final GpuBuffer[] slots = new GpuBuffer[GPU_SLOTS];
    private final AtomicIntegerArray busy = new AtomicIntegerArray(GPU_SLOTS);
    private final ArrayBlockingQueue<byte[]> free = new ArrayBlockingQueue<>(RAM_SLOTS);
    private final ArrayBlockingQueue<Frame> ready = new ArrayBlockingQueue<>(RAM_SLOTS);
    private final long startNanos = System.nanoTime();
    private long lastIndex = -1;
    private volatile boolean closing;
    private volatile boolean closed;
    private volatile String error;

    private final AtomicLong copied = new AtomicLong();
    private final AtomicLong droppedGpu = new AtomicLong();
    private final AtomicLong droppedRam = new AtomicLong();
    private final AtomicLong repeated = new AtomicLong();
    private final AtomicLong written = new AtomicLong();
    private final AtomicLong gapFrames = new AtomicLong();
    private volatile int ffmpegExit = Integer.MIN_VALUE;

    FrameRecorder(RenderTarget target, int fps, Path argsFile, Path logFile) throws IOException {
        this.width = target.width;
        this.height = target.height;
        this.fps = fps;
        this.maxRepeat = fps * 2L;
        GpuTexture tex = target.getColorTexture();
        if (tex == null) throw new IllegalStateException("framebuffer has no colour texture");
        long size = (long) width * height * tex.getFormat().blockSize();
        if (size != width * height * 4L) throw new IllegalStateException("framebuffer is not 4 bytes per pixel: " + size);
        for (int i = 0; i < GPU_SLOTS; i++) {
            final int n = i;
            slots[i] = RenderSystem.getDevice().createBuffer(() -> "nsp walk frame " + n, USAGE_MAP_READ_COPY_DST, size);
        }
        for (int i = 0; i < RAM_SLOTS; i++) free.add(new byte[(int) size]);

        List<String> cmd = new ArrayList<>();
        for (String line : Files.readAllLines(argsFile, StandardCharsets.UTF_8)) {
            if (line.isBlank()) continue;
            cmd.add(line.replace("{W}", Integer.toString(width)).replace("{H}", Integer.toString(height))
                    .replace("{FPS}", Integer.toString(fps)));
        }
        ProcessBuilder pb = new ProcessBuilder(cmd);
        pb.redirectOutput(ProcessBuilder.Redirect.DISCARD);
        pb.redirectError(logFile.toFile());
        this.ffmpeg = pb.start();
        this.sink = ffmpeg.getOutputStream();
        this.writer = new Thread(this::writeLoop, "nsp-walk-writer");
        this.writer.setDaemon(true);
        this.writer.setPriority(Thread.NORM_PRIORITY - 1);
        this.writer.start();
    }

    /** Render thread, once per frame. */
    void onFrame(RenderTarget target) {
        if (closing || error != null) return;
        if (target.width != width || target.height != height) {
            fail("framebuffer changed size to " + target.width + "x" + target.height);
            return;
        }
        long index = (System.nanoTime() - startNanos) * fps / 1_000_000_000L;
        if (index <= lastIndex) return;
        int slot = -1;
        for (int i = 0; i < GPU_SLOTS; i++) {
            if (busy.compareAndSet(i, 0, 1)) {
                slot = i;
                break;
            }
        }
        if (slot < 0) {
            droppedGpu.incrementAndGet();
            return;
        }
        lastIndex = index;
        final int s = slot;
        RenderSystem.getDevice().createCommandEncoder()
                .copyTextureToBuffer(target.getColorTexture(), slots[s], 0L, () -> onCopied(s, index), 0);
    }

    private void onCopied(int slot, long index) {
        try {
            if (closing) return;
            byte[] data = free.poll();
            if (data == null) {
                droppedRam.incrementAndGet();
                return;
            }
            try (GpuBufferSlice.MappedView view = slots[slot].map(true, false)) {
                view.data().get(0, data);
            }
            copied.incrementAndGet();
            if (!ready.offer(new Frame(data, index))) {
                free.offer(data);
                droppedRam.incrementAndGet();
            }
        } catch (Throwable t) {
            fail(t.toString());
        } finally {
            busy.set(slot, 0);
        }
    }

    private void writeLoop() {
        long base = -1;
        long next = 0;
        try {
            while (true) {
                Frame f = ready.poll(200, TimeUnit.MILLISECONDS);
                if (f == null) {
                    if (closing && ready.isEmpty()) break;
                    if (!ffmpeg.isAlive()) throw new IOException("ffmpeg exited " + ffmpeg.exitValue());
                    continue;
                }
                if (base < 0) base = f.index();
                long want = f.index() - base;
                long gap = want - next;
                if (gap > maxRepeat) { // a long stall: mark it instead of padding the clip with a frozen picture
                    gapFrames.addAndGet(gap);
                    next = want;
                }
                while (next <= want) {
                    sink.write(f.data());
                    written.incrementAndGet();
                    if (next != want) repeated.incrementAndGet();
                    next++;
                }
                free.offer(f.data());
            }
        } catch (Throwable t) {
            fail(t.toString());
        } finally {
            try {
                sink.flush();
                sink.close();
            } catch (IOException ignored) {
                // ffmpeg already gone; its log and the exit code say why
            }
            try {
                if (ffmpeg.waitFor(30, TimeUnit.SECONDS)) {
                    ffmpegExit = ffmpeg.exitValue();
                } else {
                    ffmpeg.destroyForcibly();
                    fail("ffmpeg did not finish within 30 s");
                }
            } catch (InterruptedException e) {
                ffmpeg.destroyForcibly();
            }
            closed = true;
        }
    }

    void fail(String why) {
        if (error == null) error = why;
        closing = true;
    }

    /** Asks for a clean end. Finishes on the writer thread, so the game keeps ticking while ffmpeg closes the clip. */
    void requestStop() {
        closing = true;
    }

    boolean isClosed() {
        return closed;
    }

    String error() {
        return error;
    }

    Map<String, Object> stats() {
        Map<String, Object> m = new LinkedHashMap<>();
        m.put("width", width);
        m.put("height", height);
        m.put("fps", fps);
        m.put("seconds", (System.nanoTime() - startNanos) / 1e9);
        m.put("framesCopied", copied.get());
        m.put("framesWritten", written.get());
        m.put("framesRepeated", repeated.get());
        m.put("droppedNoGpuSlot", droppedGpu.get());
        m.put("droppedNoRamSlot", droppedRam.get());
        m.put("gapFrames", gapFrames.get());
        m.put("ffmpegExit", ffmpegExit == Integer.MIN_VALUE ? null : ffmpegExit);
        m.put("error", error);
        return m;
    }

    static boolean exists(File f) {
        return f != null && f.exists();
    }
}
