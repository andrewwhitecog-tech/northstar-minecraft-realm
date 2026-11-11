"""Hosted SDL3 GL3.3 probe. Source-only unless explicitly executed; no native loads on import."""
import argparse,ctypes as C,hashlib,json,os,re,sys
from pathlib import Path
from real_glx_probe import ProbeError,hosted_guard,require,bind
SCHEMA='northstar.actual-sdl-probe.v1'
ATTRS=((17,3),(18,3),(20,1),(19,2),(22,1))
WINDOW_FLAGS=8226

def native_library(native_home,mode,env=None):
 e=os.environ if env is None else env
 require(mode in('glx','egl'),'MODE_MUST_BE_GLX_OR_EGL')
 require(native_home is not None,'NATIVE_HOME_REQUIRED')
 workspace=Path(e.get('GITHUB_WORKSPACE',''));require(bool(e.get('GITHUB_WORKSPACE'))and workspace.is_absolute(),'ABSOLUTE_GITHUB_WORKSPACE_REQUIRED')
 home=Path(native_home);require(home.is_absolute(),'ABSOLUTE_NATIVE_HOME_REQUIRED')
 root=workspace.resolve(strict=True);resolved=home.resolve(strict=True)
 require(resolved!=root and resolved.is_relative_to(root),'NATIVE_HOME_OUTSIDE_WORKSPACE')
 # Reject lexical escapes and linked components, including the workspace root.
 require(home==home.absolute()and'..'not in home.parts,'LEXICAL_NATIVE_HOME_ESCAPE')
 require(not workspace.is_symlink()and not(getattr(workspace,'is_junction',lambda:False)()),'LINKED_WORKSPACE_REFUSED')
 require(home.is_relative_to(workspace),'NATIVE_HOME_OUTSIDE_LEXICAL_WORKSPACE')
 current=workspace
 for part in home.relative_to(workspace).parts:
  current=current/part
  require(not current.is_symlink()and not(getattr(current,'is_junction',lambda:False)())and current.is_dir(),'LINKED_OR_NON_DIRECTORY_NATIVE_HOME')
 library=home/'java/libSDL3.so'
 for item in(library.parent,library):require(not item.is_symlink()and not(getattr(item,'is_junction',lambda:False)()),'LINKED_SDL_LIBRARY_REFUSED')
 require(library.parent.is_dir()and library.is_file()and library.resolve(strict=True).is_relative_to(root),'EXACT_EXISTING_SDL3_LIBRARY_REQUIRED')
 return library

def observation_ok(r):
 try:
  if not isinstance(r,dict)or r.get('cleanup_errors')!=[]or r.get('schema')!=SCHEMA or r.get('status')!='REAL_SDL_CONTEXT_QUERIED'or r.get('minecraft_client_acceptance')is not False:return False
  if r.get('hint_priority')!=2 or r.get('hint_set_result')is not True or r.get('opengl_library')!='libGL.so.1'or r.get('opengl_library_loaded')is not True:return False
  if r.get('mode')not in('glx','egl')or r.get('video_force_egl')!=('1'if r['mode']=='egl'else'0'):return False
  if r.get('driver')!='x11'or 'llvmpipe'not in r.get('renderer','').lower()or not r.get('vendor')or not r.get('version'):return False
  if type(r.get('gl_clear_error'))is not int or r['gl_clear_error']!=0:return False
  if r.get('requested_attributes')!=[list(x)for x in ATTRS]or r.get('requested_window_flags')!=WINDOW_FLAGS:return False
  actual=r['attributes']
  if not isinstance(actual,dict)or set(actual)!={str(k)for k,_ in ATTRS}or any(type(v)is not int for v in actual.values()):return False
  if(actual['17'],actual['18'])<(3,3)or actual['20']!=1 or not(actual['19']&2)or actual['22']!=1:return False
  gl=r['gl_context']
  if any(type(gl[k])is not int for k in('major','minor','profile_mask','flags')):return False
  if(gl['major'],gl['minor'])<(3,3)or gl['profile_mask']!=1 or not(gl['flags']&1):return False
  if type(r.get('window_flags'))is not int or r['window_flags']&WINDOW_FLAGS!=WINDOW_FLAGS:return False
  version=r['sdl_version']
  if not isinstance(version,list)or len(version)!=3 or any(type(n)is not int for n in version)or version[0]!=3 or version<[3,2,0]:return False
  return True
 except(KeyError,TypeError,AttributeError):return False

def probe(native_home,mode):
 report={'schema':SCHEMA,'status':'SDL_FAILED_OR_UNAVAILABLE','minecraft_client_acceptance':False,'mode':mode,'requested_attributes':[list(x)for x in ATTRS],'requested_window_flags':WINDOW_FLAGS,'stage':'hosted_guard','cleanup_errors':[]}
 sdl=None;window=None;context=None;initialized=False;gl_loaded=False
 def stage(name):report['stage']=name
 def check(ok,label):
  if not ok:
   raw=sdl.SDL_GetError()if sdl is not None else None
   raise ProbeError(label+(': '+raw.decode('utf8','replace')if raw else''))
 try:
  hosted_guard() # MUST precede all CDLL and graphics/library operations.
  for name in('MESA_GL_VERSION_OVERRIDE','MESA_GLSL_VERSION_OVERRIDE'):require(not os.environ.get(name),'GL_VERSION_OVERRIDE_REFUSED')
  stage('validate_native_library');library=native_library(native_home,mode)
  report['library']={'path':str(library),'bytes':library.stat().st_size,'sha256':hashlib.sha256(library.read_bytes()).hexdigest()}
  stage('load_sdl3');sdl=C.CDLL(str(library))
  P,I,B,S=C.c_void_p,C.c_int,C.c_bool,C.c_char_p
  for name,result,args in[
   ('SDL_SetHintWithPriority',B,[S,S,I]),('SDL_GetHint',S,[S]),('SDL_Init',B,[C.c_uint32]),('SDL_GetError',S,[]),('SDL_GetVersion',I,[]),('SDL_GetCurrentVideoDriver',S,[]),
   ('SDL_GL_LoadLibrary',B,[S]),('SDL_GL_UnloadLibrary',None,[]),('SDL_GL_SetAttribute',B,[I,I]),('SDL_GL_GetAttribute',B,[I,C.POINTER(I)]),('SDL_CreateWindow',P,[S,I,I,C.c_uint64]),('SDL_GetWindowFlags',C.c_uint64,[P]),
   ('SDL_GL_CreateContext',P,[P]),('SDL_GL_MakeCurrent',B,[P,P]),('SDL_GL_GetProcAddress',P,[S]),('SDL_GL_DestroyContext',B,[P]),('SDL_DestroyWindow',None,[P]),('SDL_QuitSubSystem',None,[C.c_uint32])]:bind(sdl,name,result,args)
  stage('set_egl_hint');hint=b'1'if mode=='egl'else b'0'
  # https://wiki.libsdl.org/SDL3/SDL_HINT_VIDEO_FORCE_EGL requires this before SDL_Init.
  # Environment values have override priority; use the same priority explicitly.
  report['hint_priority']=2;report['hint_set_result']=bool(sdl.SDL_SetHintWithPriority(b'SDL_VIDEO_FORCE_EGL',hint,2))
  check(report['hint_set_result'],'SDL_SET_EGL_HINT_FAILED')
  observed=sdl.SDL_GetHint(b'SDL_VIDEO_FORCE_EGL');check(observed==hint,'SDL_EGL_HINT_NOT_OBSERVED');report['video_force_egl']=observed.decode('ascii')
  stage('init_video');check(sdl.SDL_Init(0x20),'SDL_INIT_VIDEO_FAILED');initialized=True
  v=int(sdl.SDL_GetVersion());report['sdl_version']=[v//1000000,(v//1000)%1000,v%1000]
  driver=sdl.SDL_GetCurrentVideoDriver();check(driver,'SDL_VIDEO_DRIVER_UNAVAILABLE');report['driver']=driver.decode('utf8','replace')
  stage('load_gl_library');report['opengl_library']='libGL.so.1'
  check(sdl.SDL_GL_LoadLibrary(b'libGL.so.1'),'SDL_GL_LOAD_LIBRARY_FAILED');gl_loaded=True;report['opengl_library_loaded']=True
  stage('set_required_attributes')
  for attr,value in ATTRS:check(sdl.SDL_GL_SetAttribute(attr,value),'SDL_GL_SET_ATTRIBUTE_'+str(attr)+'_FAILED')
  stage('create_window');window=sdl.SDL_CreateWindow(b'NSP hosted GL3.3 calibration',32,32,WINDOW_FLAGS);check(window,'SDL_CREATE_WINDOW_FAILED');report['window_flags']=int(sdl.SDL_GetWindowFlags(window))
  stage('create_context');context=sdl.SDL_GL_CreateContext(window);check(context,'SDL_GL_CREATE_CONTEXT_FAILED')
  stage('make_current');check(sdl.SDL_GL_MakeCurrent(window,context),'SDL_GL_MAKE_CURRENT_FAILED')
  stage('query_attributes');report['attributes']={}
  for attr,_ in ATTRS:
   value=I();check(sdl.SDL_GL_GetAttribute(attr,C.byref(value)),'SDL_GL_GET_ATTRIBUTE_'+str(attr)+'_FAILED');report['attributes'][str(attr)]=value.value
  def gl(name,result,args):
   address=sdl.SDL_GL_GetProcAddress(name.encode('ascii'));check(address,'SDL_GL_PROC_'+name+'_UNAVAILABLE');return C.CFUNCTYPE(result,*args)(address)
  stage('query_gl');getstring=gl('glGetString',S,[C.c_uint]);getinteger=gl('glGetIntegerv',None,[C.c_uint,C.POINTER(I)])
  for name,enum in(('vendor',0x1F00),('renderer',0x1F01),('version',0x1F02)):
   raw=getstring(enum);check(raw,'GL_STRING_'+name+'_UNAVAILABLE');report[name]=raw.decode('utf8','replace')
  report['gl_context']={}
  for name,enum in(('major',0x821B),('minor',0x821C),('profile_mask',0x9126),('flags',0x821E)):
   value=I();getinteger(enum,C.byref(value));report['gl_context'][name]=value.value
  stage('clear_frame');gl('glClearColor',None,[C.c_float]*4)(.04,.05,.06,1.0);gl('glClear',None,[C.c_uint])(0x4000);gl('glFinish',None,[])();report['gl_clear_error']=int(gl('glGetError',C.c_uint,[])())
  report['status']='REAL_SDL_CONTEXT_QUERIED';stage('validate_observations')
  require(observation_ok(report),'OBSERVED_REQUIRED_CONTEXT_NOT_SATISFIED');stage('complete')
 except Exception as error:
  report.update(status='SDL_FAILED_OR_UNAVAILABLE',error_type=type(error).__name__,reason=str(error))
 finally:
  # Only handles and the video subsystem owned by this process; never quit unrelated SDL subsystems.
  if sdl is not None:
   for label,action in([('detach_context',lambda:sdl.SDL_GL_MakeCurrent(window,None)),('destroy_context',lambda:sdl.SDL_GL_DestroyContext(context))]if context else[])+([('destroy_window',lambda:sdl.SDL_DestroyWindow(window))]if window else[])+([('unload_gl_library',lambda:sdl.SDL_GL_UnloadLibrary())]if gl_loaded else[])+([('quit_video',lambda:sdl.SDL_QuitSubSystem(0x20))]if initialized else[]):
    try:
     result=action()
     if label in('detach_context','destroy_context')and not result:raise ProbeError('SDL cleanup returned false')
    except Exception as error:report['cleanup_errors'].append({'stage':label,'reason':str(error)})
  if report['cleanup_errors']:report.update(status='SDL_FAILED_OR_UNAVAILABLE',reason='OWNED_SDL_CLEANUP_FAILED')
 return report

def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--native-home',type=Path);p.add_argument('--mode',choices=('glx','egl'));a=p.parse_args(argv)
 if not a.execute:print(json.dumps({'schema':SCHEMA,'status':'SOURCE_ONLY_SDL_NOT_RUN','minecraft_client_acceptance':False}));return 0
 result=probe(a.native_home,a.mode);print(json.dumps(result));return 0 if observation_ok(result)else 2
if __name__=='__main__':sys.exit(main())
