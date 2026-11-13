"""Conservative source offer: explicitly offline synthetic-fixture service diagnostics.
Default is strict. Unknown ERROR and every FATAL remain blocking. No logs rewritten.
"""
import re
HEADER = re.compile(r'^\[(\d{2}:\d{2}:\d{2})\] \[(.+)/(TRACE|DEBUG|INFO|WARN|ERROR|FATAL)\]: (.*)$')
# Exact complete exception bodies from retained26.3 run43381942834.
# Version/stack changes fail closed pending review; substring matching is forbidden.
KNOWN_BODIES = {
  "Failed to fetch user properties": [
    "com.mojang.authlib.exceptions.InvalidCredentialsException: Status: 401",
    "\tat knot//com.mojang.authlib.exceptions.MinecraftClientHttpException.toAuthenticationException(MinecraftClientHttpException.java:70)",
    "\tat knot//com.mojang.authlib.services.MinecraftServicesUserApiService.fetchProperties(MinecraftServicesUserApiService.java:168)",
    "\tat knot//net.minecraft.client.Minecraft.lambda$new$1(Minecraft.java:451)",
    "\tat java.base/java.util.concurrent.CompletableFuture$AsyncSupply.run(CompletableFuture.java:1789)",
    "\tat java.base/java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1090)",
    "\tat java.base/java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:614)",
    "\tat java.base/java.lang.Thread.run(Thread.java:1474)",
    "Caused by: MinecraftClientHttpException[type=HTTP_ERROR, status=401, response=ErrorResponse[path=/player/attributes, error=null, errorMessage=null, details=null]]",
    "\tat knot//com.mojang.authlib.minecraft.client.MinecraftClient.buildHttpException(MinecraftClient.java:170)",
    "\tat knot//com.mojang.authlib.minecraft.client.MinecraftClient.readServiceResponse(MinecraftClient.java:147)",
    "\tat knot//com.mojang.authlib.minecraft.client.MinecraftClient.getWithEtag(MinecraftClient.java:81)",
    "\tat knot//com.mojang.authlib.minecraft.client.MinecraftClient.get(MinecraftClient.java:65)",
    "\tat knot//com.mojang.authlib.services.MinecraftServicesUserApiService.fetchProperties(MinecraftServicesUserApiService.java:118)",
    "\t... 5 more"
  ],
  "Failed to fetch Realms feature flags": [
    "com.mojang.realmsclient.exception.RealmsServiceException: Realms authentication error with message 'java.lang.RuntimeException: Failed to parse into SignedJWT: 0'",
    "\tat knot//com.mojang.realmsclient.client.RealmsClient.execute(RealmsClient.java:625)",
    "\tat knot//com.mojang.realmsclient.client.RealmsClient.fetchFeatureFlags(RealmsClient.java:204)",
    "\tat java.base/java.util.concurrent.CompletableFuture$AsyncSupply.run(CompletableFuture.java:1789)",
    "\tat java.base/java.util.concurrent.ThreadPoolExecutor.runWorker(ThreadPoolExecutor.java:1090)",
    "\tat java.base/java.util.concurrent.ThreadPoolExecutor$Worker.run(ThreadPoolExecutor.java:614)",
    "\tat java.base/java.lang.Thread.run(Thread.java:1474)"
  ]
}


def log_records(text):
    result=[]
    for number,line in enumerate(text.splitlines(),1):
        match=HEADER.fullmatch(line)
        if match:
            result.append({'line':number,'header':line,'thread':match[2], 'level':match[3], 'message':match[4], 'body':[]})
        elif re.search(r'/(?:ERROR|FATAL)\]',line):
            result.append({'line':number,'header':line,'thread':'UNPARSED','level':'ERROR','message':'UNPARSED_ERROR_OR_FATAL_HEADER','body':[]})
        elif result and line:
            result[-1]['body'].append(line)
    return result


def assess(text, *, offline_fixture=False):
    diagnostics=[];blocking=[]
    for record in log_records(text):
        if record['level'] not in ('ERROR','FATAL'):
            continue
        exact=(offline_fixture is True and record['level']=='ERROR' and
               re.fullmatch(r'Download-[0-9]+',record['thread']) is not None and
               record['message'] in KNOWN_BODIES and
               record['body']==KNOWN_BODIES[record['message']])
        (diagnostics if exact else blocking).append(record)
    return {'offlineFixture':offline_fixture is True,
            'offlineServiceDiagnostics':diagnostics,'blockingErrorRecords':blocking,
            'rendererAccepted':False,'humanVisualAccepted':False}
