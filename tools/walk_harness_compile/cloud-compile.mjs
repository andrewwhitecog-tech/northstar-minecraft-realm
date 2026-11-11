import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import crypto from 'node:crypto';
import {execFile} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const HOME=path.dirname(fileURLToPath(import.meta.url));
const ORIGINS=new Set(['https://piston-data.mojang.com','https://libraries.minecraft.net','https://maven.fabricmc.net','https://repo.maven.apache.org']);
const TEXT_FILES=new Set(['.gitignore','README.md','PUBLIC_REVIEW.md','classpath-manifest.json','cloud-compile.mjs','test/payload.test.mjs','verification/source-checks-actual.json']);
const SHA=(data,algorithm='sha256')=>crypto.createHash(algorithm).update(data).digest('hex');
async function filesUnder(root){let out=[];for(const entry of await fs.readdir(root,{withFileTypes:true})){const p=path.join(root,entry.name),s=await fs.lstat(p);if(s.isSymbolicLink())throw Error('Symlinks are not allowed');if(entry.isDirectory())out.push(...await filesUnder(p));else out.push(p);}return out;}
export async function validatePayload(root=HOME){
 const m=JSON.parse(await fs.readFile(path.join(root,'classpath-manifest.json'),'utf8'));
 if(m.target.minecraft!=='26.3'||m.target.javaRelease!==25||m.target.repository!=='andrewwhitecog-tech/northstar-minecraft-realm')throw Error('Unexpected compiler target');
 const allowed=new Set([...TEXT_FILES,...m.sources.map(s=>s.path),...m.resources.map(s=>s.path)]);
 for(const f of await filesUnder(root)){
  const rel=path.relative(root,f).split(path.sep).join('/');if(rel.startsWith('build/'))continue;
  if(!allowed.has(rel))throw Error('Unexpected public payload file: '+rel);
  const b=await fs.readFile(f);if(b.includes(0))throw Error('Binary data in public payload');
  const text=b.toString('utf8');if(/\b[A-Za-z]:[\\/]/.test(text)||/-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----/.test(text))throw Error('Private path or key material in public payload');
 }
 for(const source of [...m.sources,...m.resources]){
  if(path.isAbsolute(source.path)||source.path.split('/').includes('..'))throw Error('Unsafe source/resource path');
  const b=await fs.readFile(path.join(root,source.path));if(SHA(b)!==source.sha256)throw Error('Source/resource checksum mismatch: '+source.path);
 }
 const ids=new Set();for(const a of m.artifacts){
  const u=new URL(a.url);if(!ORIGINS.has(u.origin)||u.protocol!=='https:'||u.username||u.password||u.search||u.hash)throw Error('Unapproved dependency URL');
  if(ids.has(a.id)||!/^[a-f0-9]{40}$/.test(a.sha1)||!Number.isSafeInteger(a.size)||a.size<=0||a.size>64000000||!/^[-A-Za-z0-9_.+]+\.jar$/.test(a.filename))throw Error('Malformed pinned artifact');
  ids.add(a.id);
 }
 if(m.classpath.some(id=>!ids.has(id))||m.classpath.length!==m.legacyClasspath.entries||m.artifacts.length!==m.legacyClasspath.uniqueArtifacts)throw Error('Logical classpath mismatch');
 const mod=JSON.parse(await fs.readFile(path.join(root,'resources/fabric.mod.json'),'utf8')),mixins=JSON.parse(await fs.readFile(path.join(root,'resources/nsp_route_walk.mixins.json'),'utf8'));
 if(mod.id!=='nsp_route_walk'||mod.depends.minecraft!=='26.3'||mixins.package!=='nsp.walk.mixin'||!mixins.client.includes('MinecraftFrameMixin'))throw Error('Unexpected authentic resource contract');
 return {status:'VALIDATED_ONLY',sourceFiles:m.sources.length,resourceFiles:m.resources.length,classpathEntries:m.classpath.length,uniqueArtifacts:m.artifacts.length,compilation:'NOT_RUN',nativeProof:'NOT_RUN'};
}
export function requireHostedCI(env=process.env,platform=process.platform,release=os.release(),root=HOME){
 const needed={CI:'true',GITHUB_ACTIONS:'true',RUNNER_ENVIRONMENT:'github-hosted',RUNNER_OS:'Linux',GITHUB_REPOSITORY:'andrewwhitecog-tech/northstar-minecraft-realm',NSP_ALLOW_PUBLIC_CLOUD_JAVAC:'1',NSP_PUBLIC_REPOSITORY:'true'};
 if(platform!=='linux'||/microsoft/i.test(release)||env.WSL_DISTRO_NAME||env.WSL_INTEROP)throw Error('Compilation refused: genuine hosted Linux CI only; no local or WSL build');
 for(const[k,v]of Object.entries(needed))if(env[k]!==v)throw Error('Compilation refused: required hosted public-CI declaration '+k);
 if(!env.GITHUB_WORKSPACE?.startsWith('/home/runner/work/')||!env.RUNNER_TEMP?.startsWith('/home/runner/'))throw Error('Compilation refused: unexpected hosted-runner workspace');
 const relative=path.relative(env.GITHUB_WORKSPACE,root);if(relative==='..'||relative.startsWith('../')||path.isAbsolute(relative))throw Error('Compilation refused: payload outside CI checkout');
}
async function run(exe,args,root){return await new Promise((resolve,reject)=>{const child=execFile(exe,args,{cwd:root,windowsHide:true,encoding:'utf8',timeout:60000,maxBuffer:1000000},(error,stdout,stderr)=>error?reject(Error(exe+' failed: '+stderr.slice(-5000))):resolve({stdout,stderr}));child.stdin.end();});}
async function download(a,directory){
 const file=path.join(directory,a.id+'-'+a.filename);
 const verify=b=>b.length===a.size&&SHA(b,'sha1')===a.sha1;
 try{const b=await fs.readFile(file);if(!verify(b))throw Error('Cached dependency checksum mismatch');return file;}catch(e){if(e.code!=='ENOENT')throw e;}
 const r=await fetch(a.url,{redirect:'error',signal:AbortSignal.timeout(60000)});if(!r.ok)throw Error('Official dependency HTTP '+r.status+' for '+a.coordinate);
 const declared=Number(r.headers.get('content-length'));if(declared&&declared!==a.size)throw Error('Dependency length changed');
 const chunks=[];let bytes=0;for await(const chunk of r.body){bytes+=chunk.length;if(bytes>a.size)throw Error('Dependency exceeds published size');chunks.push(chunk);}const b=Buffer.concat(chunks);
 if(!verify(b))throw Error('Official dependency checksum mismatch for '+a.coordinate);await fs.writeFile(file,b,{flag:'wx'});return file;
}
export async function compileHosted(root=HOME){
 requireHostedCI(process.env,process.platform,os.release(),root);await validatePayload(root);
 const started=Date.now(),m=JSON.parse(await fs.readFile(path.join(root,'classpath-manifest.json'),'utf8'));
 const build=path.join(root,'build'),classes=path.join(build,'classes'),deps=path.join(build,'dependencies');
 await fs.mkdir(classes,{recursive:true});await fs.mkdir(deps,{recursive:true});if((await fs.readdir(classes)).length)throw Error('Refusing stale compiler output; use a fresh hosted checkout');
 const resolved=new Map();let cursor=0;await Promise.all(Array.from({length:4},async()=>{while(cursor<m.artifacts.length){const a=m.artifacts[cursor++];resolved.set(a.id,await download(a,deps));}}));
 const cp=m.classpath.map(id=>path.relative(root,resolved.get(id))).join(path.delimiter);
 const args=['--release','25','-proc:none','-encoding','UTF-8','-cp',cp,'-d','build/classes',...m.sources.map(s=>s.path)];
 await fs.writeFile(path.join(build,'javac.args'),args.map(a=>JSON.stringify(a)).join('\n')+'\n');
 const jdk=await run('javac',['-version'],root);if(!/javac 25(?:\.|\s|$)/.test(jdk.stdout+jdk.stderr))throw Error('JDK25 required');
 await run('javac',['-J-XX:ActiveProcessorCount=1','-J-XX:+UseSerialGC','-J-Xms32m','-J-Xmx384m','@build/javac.args'],root);
 const compiled=(await filesUnder(classes)).map(f=>path.relative(classes,f).split(path.sep).join('/'));
 if(!compiled.length||compiled.some(f=>!f.startsWith('nsp/walk/')||!f.endsWith('.class')))throw Error('Unexpected classes; refusing dependency shading');
 const name='nsp-route-walk-heldproof-v02-'+m.sources.find(s=>s.path.endsWith('/RouteWalk.java')).sha256.slice(0,12)+'.jar',jarRelative='build/'+name;
 await run('jar',['--create','--file',jarRelative,'--no-manifest','-C','build/classes','.','-C','resources','.'],root);
 const listing=(await run('jar',['--list','--file',jarRelative],root)).stdout.trim().split(/\r?\n/);
 if(listing.some(f=>!f.startsWith('nsp/')&&!m.resources.some(r=>r.path==='resources/'+f)))throw Error('Unexpected JAR contents');
 const binary=await fs.readFile(path.join(root,jarRelative));if(binary.length<=0||binary.length>1000000)throw Error('Candidate JAR exceeds log-delivery bound');
 const result={status:'COMPILED_CANDIDATE_ONLY',filename:name,size:binary.length,sha256:SHA(binary),classFiles:compiled.length,resourceFiles:m.resources.length,elapsedMs:Date.now()-started,javac:jdk.stdout.trim()||jdk.stderr.trim(),nativeProof:'NOT_RUN',installed:false,delivery:'bounded job-log base64; no artifact/cache storage'};
 await fs.writeFile(path.join(build,'compile-result.json'),JSON.stringify(result,null,2));
 console.log('NSP_JAR_METADATA '+JSON.stringify(result));console.log('NSP_JAR_BASE64_BEGIN');const b64=binary.toString('base64');for(let i=0;i<b64.length;i+=8192)console.log(b64.slice(i,i+8192));console.log('NSP_JAR_BASE64_END');
 return result;
}
async function main(){const args=process.argv.slice(2);if(args.length>1||args.length&& !['--validate','--compile'].includes(args[0]))throw Error('Use --validate (default) or --compile');if(args[0]==='--compile')await compileHosted();else console.log(JSON.stringify(await validatePayload()));}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url))main().catch(error=>{console.error(error.message);process.exitCode=2;});
