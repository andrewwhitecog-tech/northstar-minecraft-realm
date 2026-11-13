package nsp.walk;

import static org.junit.jupiter.api.Assertions.*;
import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.OutputStream;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;
import org.junit.jupiter.api.Test;

/** Synthetic queue/I/O unit cases only. They do not create a framebuffer, ffmpeg, game or native proof. */
final class FrameRecorderUniqueWriterTest {
    private static void drain(FrameRecorder.UniqueWriter queue, OutputStream sink, List<byte[]> recycled) throws Exception {
        queue.drain(sink, () -> true, () -> 0, recycled::add, () -> false, () -> 0L);
    }

    @Test void shortSamplingGapNeverPadsWithDuplicateFrameBytes() throws Exception {
        var queue = new FrameRecorder.UniqueWriter(4, 48);
        var sink = new ByteArrayOutputStream(); var recycled = new ArrayList<byte[]>();
        assertTrue(queue.offer(new byte[]{1,2,3,4},1,10));
        assertTrue(queue.offer(new byte[]{5,6,7,8},2,12));
        assertTrue(queue.offer(new byte[]{9,10,11,12},3,13));
        queue.finishProducer(); drain(queue,sink,recycled);
        assertArrayEquals(new byte[]{1,2,3,4,5,6,7,8,9,10,11,12},sink.toByteArray());
        assertEquals(3,queue.written.get()); assertEquals(3,queue.uniqueWritten.get());
        assertEquals(1,queue.samplingIntervalsSkipped.get()); assertEquals(0,queue.gapFrames.get());
        assertEquals(0,queue.sequenceGaps.get()); assertEquals(3,recycled.size());
    }

    @Test void fullQueueDoesNotLoseLastFramesWhenEndMarkerCannotFit() throws Exception {
        var queue = new FrameRecorder.UniqueWriter(2,48); var sink = new ByteArrayOutputStream();
        var recycled = new ArrayList<byte[]>();
        assertTrue(queue.offer(new byte[]{21},1,0));assertTrue(queue.offer(new byte[]{22},2,1));
        queue.finishProducer();drain(queue,sink,recycled);
        assertArrayEquals(new byte[]{21,22},sink.toByteArray());assertEquals(2,queue.written.get());
    }

    @Test void alreadyIssuedCallbackMayPublishBeforeProducerFinishedAndIsDrained() throws Exception {
        var queue = new FrameRecorder.UniqueWriter(4,48);var sink = new ByteArrayOutputStream();
        var firstWritten = new CountDownLatch(1);var failure = new AtomicReference<Throwable>();
        assertTrue(queue.offer(new byte[]{31},1,0));
        Thread worker = new Thread(() -> {
            try {queue.drain(sink,()->true,()->0,data->firstWritten.countDown(),()->true,System::nanoTime);}
            catch(Throwable error){failure.set(error);}
        });
        worker.start();
        try {
            assertTrue(firstWritten.await(3,TimeUnit.SECONDS));
            assertTrue(worker.isAlive(),"A temporary empty queue is not producer completion");
            assertTrue(queue.offer(new byte[]{32},2,1));queue.finishProducer();
            worker.join(3000);assertFalse(worker.isAlive(),"End marker must wake/drain the writer");
            assertNull(failure.get());assertArrayEquals(new byte[]{31,32},sink.toByteArray());
            assertEquals(2,queue.written.get());
        } finally {queue.finishProducer();worker.interrupt();worker.join(3000);}
    }

    @Test void duplicateSequenceIsRejectedBeforeSecondSinkWrite() throws Exception {
        var queue = new FrameRecorder.UniqueWriter(4,48);var sink = new ByteArrayOutputStream();
        assertTrue(queue.offer(new byte[]{41},1,0));assertTrue(queue.offer(new byte[]{42},1,1));
        queue.finishProducer();var recycled = new ArrayList<byte[]>();
        assertThrows(IOException.class,()->drain(queue,sink,recycled));
        assertArrayEquals(new byte[]{41},sink.toByteArray());assertEquals(1,queue.rejectedOrder.get());
        assertEquals(1,queue.written.get());assertEquals(2,recycled.size());
    }

    @Test void backwardsSamplingIdentityIsRejectedBeforeSecondSinkWrite() throws Exception {
        var queue = new FrameRecorder.UniqueWriter(4,48);var sink = new ByteArrayOutputStream();
        assertTrue(queue.offer(new byte[]{51},1,5));assertTrue(queue.offer(new byte[]{52},2,4));
        queue.finishProducer();assertThrows(IOException.class,()->drain(queue,sink,new ArrayList<>()));
        assertArrayEquals(new byte[]{51},sink.toByteArray());assertEquals(1,queue.rejectedOrder.get());
    }

    @Test void longGapAndMissingProducerSequenceRemainVisible() throws Exception {
        var queue = new FrameRecorder.UniqueWriter(4,2);var sink = new ByteArrayOutputStream();
        assertTrue(queue.offer(new byte[]{61},1,0));assertTrue(queue.offer(new byte[]{62},3,5));
        queue.finishProducer();drain(queue,sink,new ArrayList<>());
        assertArrayEquals(new byte[]{61,62},sink.toByteArray());assertEquals(4,queue.gapFrames.get());
        assertEquals(4,queue.samplingIntervalsSkipped.get());assertEquals(1,queue.sequenceGaps.get());
    }

    @Test void sinkFailureIsNotConvertedIntoAnAcceptedFrame() throws Exception {
        var queue = new FrameRecorder.UniqueWriter(2,48);assertTrue(queue.offer(new byte[]{71},1,0));
        queue.finishProducer();var recycled = new ArrayList<byte[]>();
        OutputStream broken = new OutputStream(){@Override public void write(int value)throws IOException{throw new IOException("UNIT sink failure");}};
        assertThrows(IOException.class,()->drain(queue,broken,recycled));
        assertEquals(0,queue.written.get());assertEquals(0,queue.uniqueWritten.get());assertEquals(1,recycled.size());
    }

    @Test void latePublishAndStalledProducerRemainFailures() {
        var finished = new FrameRecorder.UniqueWriter(1,48);finished.finishProducer();
        assertThrows(IllegalStateException.class,()->finished.offer(new byte[]{81},1,0));
        var stalled = new FrameRecorder.UniqueWriter(1,48);
        assertThrows(IOException.class,()->stalled.drain(new ByteArrayOutputStream(),()->true,()->0,data->{},()->true,
            ()->System.nanoTime()-TimeUnit.SECONDS.toNanos(11)));
    }
}
