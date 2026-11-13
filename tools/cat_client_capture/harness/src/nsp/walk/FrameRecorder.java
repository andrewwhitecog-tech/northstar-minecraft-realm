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
import java.util.function.BooleanSupplier;
import java.util.function.IntSupplier;
import java.util.function.LongSupplier;
import java.util.function.Consumer;

/**
 * Copies the game's own framebuffer to raw RGBA frames and pipes them to ffmpeg's stdin.
 * Nothing here touches the desktop, so a hidden window records fine and Andrew's screen can never leak in.
 *
 * Render thread: picks frames on a fixed 1/fps clock and asks the GPU to copy them into a small ring of read buffers.
 * Writer thread: feeds each genuinely copied framebuffer once. Missed sampling indices are reported, never padded.
 * Both ends are bounded. If anything lags, frames are dropped and counted; the game never stalls waiting for the disk.
 */
final class FrameRecorder {
    private static final int GPU_SLOTS = 4;
    private static final int RAM_SLOTS = 6;
    private static final int USAGE_MAP_READ_COPY_DST = 9; // the usage flags Mojang's Screenshot class passes

    private record Frame(byte[] data, long sequence, long index) {}

    private final int width;
    private final int height;
    private final int fps;
    private final UniqueWriter queueWriter;
    private final Object producerLock = new Object();
    private final Process ffmpeg;
    private final OutputStream sink;
    private final Thread writer;
    private final GpuBuffer[] slots = new GpuBuffer[GPU_SLOTS];
    private final AtomicIntegerArray busy = new AtomicIntegerArray(GPU_SLOTS);
    private final ArrayBlockingQueue<byte[]> free = new ArrayBlockingQueue<>(RAM_SLOTS);
    private final long startNanos = System.nanoTime();
    private long lastIndex = -1;
    private volatile boolean closing;
    private volatile boolean producerFinished;
    private volatile long stopRequestedNanos;
    private volatile boolean closed;
    private volatile String error;

    private final AtomicLong copied = new AtomicLong();
    private final AtomicLong droppedGpu = new AtomicLong();
    private final AtomicLong droppedRam = new AtomicLong();
    private final AtomicLong submitted = new AtomicLong();
    private final AtomicLong callbacksAfterClose = new AtomicLong();
    private volatile int ffmpegExit = Integer.MIN_VALUE;

    FrameRecorder(RenderTarget target, int fps, Path argsFile, Path logFile) throws IOException {
        this.width = target.width;
        this.height = target.height;
        this.fps = fps;
        this.queueWriter = new UniqueWriter(RAM_SLOTS, fps * 2L);
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

    /** Render thread, once per frame. No new copies are admitted after stop. */
    void onFrame(RenderTarget target) {
        synchronized (producerLock) {
            if (closing || error != null) return;
            if (target.width != width || target.height != height) {
                fail("framebuffer changed size to " + target.width + "x" + target.height);
                return;
            }
            long index = (System.nanoTime() - startNanos) * fps / 1_000_000_000L;
            if (index <= lastIndex) return;
            int slot = -1;
            for (int i = 0; i < GPU_SLOTS; i++) {
                if (busy.compareAndSet(i, 0, 1)) { slot = i; break; }
            }
            if (slot < 0) { droppedGpu.incrementAndGet(); return; }
            lastIndex = index;
            final int selected = slot;
            final long sequence = submitted.incrementAndGet();
            try {
                RenderSystem.getDevice().createCommandEncoder()
                    .copyTextureToBuffer(target.getColorTexture(), slots[selected], 0L,
                        () -> onCopied(selected, sequence, index), 0);
            } catch (Throwable failure) {
                busy.set(selected, 0);
                fail(failure.toString());
                finishProducerIfDrained();
            }
        }
    }

    private void onCopied(int slot, long sequence, long index) {
        try {
            // Stop forbids new submissions, but every already-issued callback must still drain.
            if (closed) {
                callbacksAfterClose.incrementAndGet();
                fail("GPU copy callback arrived after writer closure");
                return;
            }
            byte[] data = free.poll();
            if (data == null) { droppedRam.incrementAndGet(); return; }
            try (GpuBufferSlice.MappedView view = slots[slot].map(true, false)) {
                view.data().get(0, data);
            }
            copied.incrementAndGet();
            if (!queueWriter.offer(data, sequence, index)) {
                free.offer(data);
                droppedRam.incrementAndGet();
            }
        } catch (Throwable failure) {
            fail(failure.toString());
        } finally {
            busy.set(slot, 0);
            finishProducerIfDrained();
        }
    }

    private int pendingCopies() {
        int pending = 0;
        for (int i = 0; i < GPU_SLOTS; i++) pending += busy.get(i);
        return pending;
    }

    private void finishProducerIfDrained() {
        synchronized (producerLock) {
            if (closing && !producerFinished && pendingCopies() == 0) {
                producerFinished = true;
                queueWriter.finishProducer(); // Wake an empty-queue writer immediately; no 200ms stop tail.
            }
        }
    }

    private void writeLoop() {
        try {
            queueWriter.drain(sink, ffmpeg::isAlive, ffmpeg::exitValue, free::offer,
                () -> closing, () -> stopRequestedNanos);
            if (!producerFinished || queueWriter.written.get() != copied.get()) {
                throw new IOException("Producer/queue did not drain every copied frame");
            }
        } catch (Throwable failure) {
            fail(failure.toString());
        } finally {
            try { sink.flush(); sink.close(); } catch (IOException ignored) {
                // ffmpeg log and exit status remain authoritative.
            }
            try {
                if (ffmpeg.waitFor(30, TimeUnit.SECONDS)) ffmpegExit = ffmpeg.exitValue();
                else { ffmpeg.destroyForcibly(); fail("ffmpeg did not finish within 30 s"); }
            } catch (InterruptedException interrupted) {
                Thread.currentThread().interrupt();
                ffmpeg.destroyForcibly();
                fail("writer interrupted while awaiting ffmpeg");
            }
            closed = true;
        }
    }

    /** Pure queue/I/O core: unit-testable without constructing a GPU recorder or launching ffmpeg. */
    static final class UniqueWriter {
        private static final Frame END = new Frame(null, -1, -1);
        private final ArrayBlockingQueue<Frame> ready;
        private final long longGapThreshold;
        private volatile boolean producerFinished;
        final AtomicLong written = new AtomicLong();
        final AtomicLong uniqueWritten = new AtomicLong();
        final AtomicLong samplingIntervalsSkipped = new AtomicLong();
        final AtomicLong gapFrames = new AtomicLong();
        final AtomicLong sequenceGaps = new AtomicLong();
        final AtomicLong rejectedOrder = new AtomicLong();
        final AtomicLong firstSequence = new AtomicLong(-1);
        final AtomicLong lastSequence = new AtomicLong(-1);
        final AtomicLong lastSamplingIndex = new AtomicLong(-1);

        UniqueWriter(int capacity, long longGapThreshold) {
            if (capacity < 1 || longGapThreshold < 0) throw new IllegalArgumentException("Bounded queue required");
            this.ready = new ArrayBlockingQueue<>(capacity);
            this.longGapThreshold = longGapThreshold;
        }

        boolean offer(byte[] data, long sequence, long samplingIndex) {
            if (data == null || sequence < 1 || samplingIndex < 0) throw new IllegalArgumentException("Real frame identity required");
            if (producerFinished) throw new IllegalStateException("Frame after producer finished");
            return ready.offer(new Frame(data, sequence, samplingIndex));
        }

        void finishProducer() {
            producerFinished = true;
            ready.offer(END); // If full, real queued frames already wake the consumer; its next empty check exits.
        }

        void drain(OutputStream sink, BooleanSupplier encoderAlive, IntSupplier encoderExit,
                   Consumer<byte[]> recycle, BooleanSupplier stopping, LongSupplier stopTime)
                   throws IOException, InterruptedException {
            long previousSequence = 0;
            long previousIndex = -1;
            while (true) {
                if (producerFinished && ready.isEmpty()) return;
                if (stopping.getAsBoolean() && !producerFinished && stopTime.getAsLong() > 0
                    && System.nanoTime() - stopTime.getAsLong() > TimeUnit.SECONDS.toNanos(10)) {
                    throw new IOException("Already-issued GPU copies did not finish within 10 s");
                }
                Frame frame = ready.poll(200, TimeUnit.MILLISECONDS);
                if (frame == null) {
                    if (!encoderAlive.getAsBoolean()) throw new IOException("ffmpeg exited " + encoderExit.getAsInt());
                    continue;
                }
                if (frame == END) continue;
                try {
                    if (frame.sequence() <= previousSequence || frame.index() <= previousIndex) {
                        rejectedOrder.incrementAndGet();
                        throw new IOException("Duplicate/out-of-order framebuffer identity");
                    }
                    sequenceGaps.addAndGet(frame.sequence() - previousSequence - 1);
                    long missed = previousIndex < 0 ? 0 : frame.index() - previousIndex - 1;
                    samplingIntervalsSkipped.addAndGet(missed);
                    // Keep original gapFrames meaning: only stalls longer than fps*2 were counted there.
                    if (missed > longGapThreshold) gapFrames.addAndGet(missed);
                    sink.write(frame.data()); // Exactly ONE write for this actual GPU-copy sequence.
                    written.incrementAndGet();
                    uniqueWritten.incrementAndGet();
                    if (firstSequence.get() < 0) firstSequence.set(frame.sequence());
                    lastSequence.set(frame.sequence());
                    lastSamplingIndex.set(frame.index());
                    previousSequence = frame.sequence();
                    previousIndex = frame.index();
                } finally { recycle.accept(frame.data()); }
            }
        }

        void appendStats(Map<String,Object> stats) {
            stats.put("framesWritten", written.get());
            stats.put("uniqueFramesWritten", uniqueWritten.get());
            stats.put("framesRepeated", written.get() - uniqueWritten.get());
            stats.put("samplingIntervalsSkipped", samplingIntervalsSkipped.get());
            stats.put("gapFrames", gapFrames.get());
            stats.put("sourceSequenceGaps", sequenceGaps.get());
            stats.put("duplicateOrOutOfOrderRejected", rejectedOrder.get());
            stats.put("firstWrittenSequence", firstSequence.get());
            stats.put("lastWrittenSequence", lastSequence.get());
            stats.put("lastWrittenSamplingIndex", lastSamplingIndex.get());
            stats.put("writerProducerFinished", producerFinished);
        }
    }

    void fail(String why) {
        if (error == null) error = why;
        requestStop();
    }

    /** Asks for a clean end. Finishes on the writer thread, so the game keeps ticking while ffmpeg closes the clip. */
    void requestStop() {
        synchronized (producerLock) {
            if (!closing) { stopRequestedNanos = System.nanoTime(); closing = true; }
        }
        finishProducerIfDrained();
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
        queueWriter.appendStats(m);
        m.put("framesSubmitted", submitted.get());
        m.put("pendingGpuCopiesAtClose", pendingCopies());
        m.put("callbacksAfterWriterClose", callbacksAfterClose.get());
        m.put("sourceFrameSequenceConsistent", producerFinished && pendingCopies() == 0
            && submitted.get() == copied.get() && copied.get() == queueWriter.written.get()
            && queueWriter.written.get() == queueWriter.uniqueWritten.get()
            && queueWriter.sequenceGaps.get() == 0 && queueWriter.rejectedOrder.get() == 0
            && callbacksAfterClose.get() == 0);
        m.put("droppedNoGpuSlot", droppedGpu.get());
        m.put("droppedNoRamSlot", droppedRam.get());
        m.put("ffmpegExit", ffmpegExit == Integer.MIN_VALUE ? null : ffmpegExit);
        m.put("error", error);
        return m;
    }

    static boolean exists(File f) {
        return f != null && f.exists();
    }
}
