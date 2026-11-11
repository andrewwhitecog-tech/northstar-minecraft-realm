"""Actual existing-library GLX probe. SOURCE ONLY by default; no library loads on import."""
import argparse,ctypes as C,json,os,platform,re,sys
class ProbeError(Exception):pass
def require(ok,message):
 if not ok:raise ProbeError(message)
def hosted_guard(env=None,system=None,kernel=None):
 e=os.environ if env is None else env
 require((system or platform.system())=='Linux' and 'microsoft' not in (kernel or platform.release()).lower() and not e.get('WSL_INTEROP') and not e.get('WSL_DISTRO_NAME'),'HOSTED_LINUX_ONLY')
 for k,v in {'CI':'true','GITHUB_ACTIONS':'true','RUNNER_ENVIRONMENT':'github-hosted','RUNNER_OS':'Linux','ImageOS':'ubuntu24','GITHUB_EVENT_NAME':'workflow_dispatch','GITHUB_REF':'refs/heads/main','GITHUB_REPOSITORY':'andrewwhitecog-tech/northstar-minecraft-realm','NSP_ALLOW_CLOUD_SURVIVAL_CALIBRATION':'1'}.items():require(e.get(k)==v,'HOST_CONTEXT_'+k)
 require(re.fullmatch(r':[0-9]{1,3}(?:\.0)?',e.get('DISPLAY','')) is not None,'OWN_X_DISPLAY_REQUIRED')
 require(e.get('LIBGL_ALWAYS_SOFTWARE')=='1' and e.get('GALLIUM_DRIVER')=='llvmpipe','SOFTWARE_DRIVER_REQUIRED')
class XVisualInfo(C.Structure):
 _fields_=[('visual',C.c_void_p),('visualid',C.c_ulong),('screen',C.c_int),('depth',C.c_int),('visual_class',C.c_int),('red_mask',C.c_ulong),('green_mask',C.c_ulong),('blue_mask',C.c_ulong),('colormap_size',C.c_int),('bits_per_rgb',C.c_int)]
class XSetWindowAttributes(C.Structure):
 _fields_=[('background_pixmap',C.c_ulong),('background_pixel',C.c_ulong),('border_pixmap',C.c_ulong),('border_pixel',C.c_ulong),('bit_gravity',C.c_int),('win_gravity',C.c_int),('backing_store',C.c_int),('backing_planes',C.c_ulong),('backing_pixel',C.c_ulong),('save_under',C.c_int),('event_mask',C.c_long),('do_not_propagate_mask',C.c_long),('override_redirect',C.c_int),('colormap',C.c_ulong),('cursor',C.c_ulong)]
def bind(lib,name,result,args):
 f=getattr(lib,name);f.restype=result;f.argtypes=args;return f
def probe():
 hosted_guard() # Before CDLL or any X11/OpenGL/native call.
 P,U,I=C.c_void_p,C.c_ulong,C.c_int
 try:x=C.CDLL('libX11.so.6');g=C.CDLL('libGL.so.1')
 except OSError:raise ProbeError('EXISTING_X11_OR_GL_LIBRARY_UNAVAILABLE') from None
 bind(x,'XOpenDisplay',P,[C.c_char_p]);bind(x,'XDefaultScreen',I,[P]);bind(x,'XRootWindow',U,[P,I]);bind(x,'XCreateColormap',U,[P,U,P,I]);bind(x,'XCreateWindow',U,[P,U,I,I,C.c_uint,C.c_uint,C.c_uint,I,C.c_uint,P,U,C.POINTER(XSetWindowAttributes)]);bind(x,'XMapWindow',I,[P,U]);bind(x,'XSync',I,[P,I]);bind(x,'XDestroyWindow',I,[P,U]);bind(x,'XFreeColormap',I,[P,U]);bind(x,'XFree',I,[P]);bind(x,'XCloseDisplay',I,[P])
 bind(g,'glXQueryVersion',I,[P,C.POINTER(I),C.POINTER(I)]);bind(g,'glXChooseVisual',C.POINTER(XVisualInfo),[P,I,C.POINTER(I)]);bind(g,'glXCreateContext',P,[P,C.POINTER(XVisualInfo),P,I]);bind(g,'glXMakeCurrent',I,[P,U,P]);bind(g,'glXDestroyContext',None,[P,P]);bind(g,'glXIsDirect',I,[P,P]);bind(g,'glGetString',C.c_char_p,[C.c_uint]);bind(g,'glClearColor',None,[C.c_float]*4);bind(g,'glClear',None,[C.c_uint]);bind(g,'glFinish',None,[]);bind(g,'glGetError',C.c_uint,[])
 display=None;visual=None;colormap=0;window=0;context=None;current=False
 try:
  display=x.XOpenDisplay(os.environ['DISPLAY'].encode());require(display,'X_OPEN_DISPLAY_FAILED')
  major,minor=I(),I();require(g.glXQueryVersion(display,C.byref(major),C.byref(minor)),'GLX_EXTENSION_UNAVAILABLE')
  # GLX_RGBA, DOUBLEBUFFER, RED/GREEN/BLUE8, ALPHA8, DEPTH24, None.
  attrs=(I*13)(4,5,8,8,9,8,10,8,11,8,12,24,0)
  visual=g.glXChooseVisual(display,x.XDefaultScreen(display),attrs);require(visual,'GLX_CHOOSE_VISUAL_FAILED')
  v=visual.contents;root=x.XRootWindow(display,v.screen)
  colormap=x.XCreateColormap(display,root,v.visual,0);require(colormap,'X_COLORMAP_FAILED')
  swa=XSetWindowAttributes();swa.colormap=colormap;swa.border_pixel=0
  # CWBorderPixel | CWColormap; window uses the chosen visual's actual depth.
  window=x.XCreateWindow(display,root,0,0,32,32,0,v.depth,1,v.visual,(1<<3)|(1<<13),C.byref(swa));require(window,'X_WINDOW_FAILED')
  x.XMapWindow(display,window);x.XSync(display,0)
  context=g.glXCreateContext(display,visual,None,1);require(context,'GLX_CREATE_CONTEXT_FAILED')
  require(g.glXMakeCurrent(display,window,context),'GLX_MAKE_CURRENT_FAILED');current=True
  strings={}
  for name,enum in [('vendor',0x1F00),('renderer',0x1F01),('version',0x1F02)]:
   raw=g.glGetString(enum);require(raw,'GL_GET_STRING_'+name.upper()+'_FAILED');strings[name]=raw.decode('utf8','replace')
  g.glClearColor(.04,.05,.06,1.0);g.glClear(0x4000);g.glFinish();error=int(g.glGetError());require(error==0,'GL_CLEAR_ERROR_'+str(error))
  return {'schema':'northstar.actual-glx-probe.v1','status':'REAL_GLX_CONTEXT_QUERIED','glx_version':[major.value,minor.value],'visual_id':int(v.visualid),'visual_depth':v.depth,'direct':bool(g.glXIsDirect(display,context)),**strings,'gl_clear_error':error,'minecraft_client_acceptance':False}
 finally:
  # Exact handles created above only; detach BEFORE context/window/display destruction.
  if display:
   if current:g.glXMakeCurrent(display,0,None)
   if context:g.glXDestroyContext(display,context)
   if window:x.XDestroyWindow(display,window)
   if colormap:x.XFreeColormap(display,colormap)
   if visual:x.XFree(C.cast(visual,P))
   x.XCloseDisplay(display)
def main():
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');a=p.parse_args()
 if not a.execute:print(json.dumps({'status':'SOURCE_ONLY_GLX_NOT_RUN'}));return 0
 try:result=probe();print(json.dumps(result));return 0
 except ProbeError as e:print(json.dumps({'schema':'northstar.actual-glx-probe.v1','status':'GLX_FAILED_OR_UNAVAILABLE','reason':str(e),'minecraft_client_acceptance':False}));return 2
 except Exception:print(json.dumps({'schema':'northstar.actual-glx-probe.v1','status':'GLX_FAILED_OR_UNAVAILABLE','reason':'UNEXPECTED_PROBE_FAILURE','minecraft_client_acceptance':False}));return 2
if __name__=='__main__':sys.exit(main())
