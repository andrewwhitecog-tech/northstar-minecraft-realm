package nsp.walk;
import java.io.*;import java.nio.charset.StandardCharsets;import java.nio.file.*;import java.util.*;
/** Bounded sequential genuine RGBA sink; no encoder/process exists during capture. */
final class RawFrameSpool implements AutoCloseable {
 final Path rawPath,indexPath;final long frameBytes,maxFrames;private final OutputStream file;private final BufferedWriter index;
 private long bytes,frames,lastSequence,lastSampling=-1;private boolean closed;
 RawFrameSpool(Path base,long frameBytes,long maxFrames)throws IOException{
  if(frameBytes<1||frameBytes>Integer.MAX_VALUE||maxFrames<1||maxFrames>600)throw new IllegalArgumentException("Finite genuine raw spool bound required");
  this.frameBytes=frameBytes;this.maxFrames=maxFrames;rawPath=base.resolveSibling(base.getFileName()+".rgba");indexPath=base.resolveSibling(base.getFileName()+".frames.jsonl");
  file=Files.newOutputStream(rawPath,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);
  BufferedWriter opened=null;try{opened=Files.newBufferedWriter(indexPath,StandardCharsets.UTF_8,StandardOpenOption.CREATE_NEW,StandardOpenOption.WRITE);}catch(IOException failure){file.close();throw failure;}index=opened;
 }
 OutputStream output(){return new OutputStream(){public void write(int ignored)throws IOException{throw new IOException("Whole genuine frame writes only");}public void write(byte[]data)throws IOException{write(data,0,data.length);}public void write(byte[]data,int off,int len)throws IOException{
  if(closed||off!=0||len!=frameBytes||bytes+len>frameBytes*maxFrames)throw new IOException("Raw spool closed/frame width/finite capacity violated");file.write(data,off,len);bytes+=len;
 }public void flush()throws IOException{file.flush();}public void close(){} };}
 void recordFrame(long sequence,long samplingIndex,int length)throws IOException{
  if(closed||length!=frameBytes||bytes!=(frames+1)*frameBytes||sequence<=lastSequence||samplingIndex<=lastSampling)throw new IOException("Actual spool identity/byte position invalid");
  index.write("{\"sequence\":"+sequence+",\"samplingIndex\":"+samplingIndex+",\"offset\":"+(frames*frameBytes)+",\"bytes\":"+length+"}\n");frames++;lastSequence=sequence;lastSampling=samplingIndex;
 }
 public void close()throws IOException{if(closed)return;IOException error=null;try{file.close();}catch(IOException e){error=e;}try{index.close();}catch(IOException e){if(error==null)error=e;else error.addSuppressed(e);}closed=true;if(error!=null)throw error;if(Files.size(rawPath)!=bytes||bytes!=frames*frameBytes)throw new IOException("Actual closed spool length/index differs");}
 Map<String,Object> stats(){Map<String,Object> s=new LinkedHashMap<>();s.put("rawPath",rawPath.toString());s.put("indexPath",indexPath.toString());s.put("frameBytes",frameBytes);s.put("maximumFrames",maxFrames);s.put("writtenBytes",bytes);s.put("indexedFrames",frames);s.put("closed",closed);return s;}
}
