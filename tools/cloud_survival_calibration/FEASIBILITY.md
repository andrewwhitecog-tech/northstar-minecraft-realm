# Feasibility and exact dependency evidence

Prepared2026-11-11T14:50:47.969Z; native execution remains NOT_RUN.

## Source-backed feasible route

- Official Mojang manifest lists26.3; package URL https://piston-meta.mojang.com/v1/packages/9f67e10ed013deeaad20ac3c800652765d493408/26.3.json. Its SHA1 9f67e10ed013deeaad20ac3c800652765d493408 matches the live manifest’s version entry. Actual metadata requires Java25, client main net.minecraft.client.main.Main,114library rows and assets index34.
- Client artifact41,483,720B SHA1 e877b6a07acd633fb3bb475002175cec036e7b87. Server bundle62,294,556B SHA1 33680f5f2ac32864d6d7cf5e56a705fdb3e05f4c. Root’s retained public server-transport manifest pins its exact40 extracted classpath members separately; no private server files are copied.
- Official asset index https://piston-meta.mojang.com/v1/packages/e99f9973047785b5a9d52eaf72020b97545053c9/34.json:597,235B,5149logical entries, nominal total487,358,754B. Runtime deduplicates content hashes; no binary assets are in this payload. With client/server/libraries/mods, acquisition is bounded to950,000,000downloadedbytes,8asset-download workers,80MiB/file,600s preparation.
- Official Fabric profiles: https://meta.fabricmc.net/v2/versions/loader/26.3/0.20.1/profile/json and /server/json. Pinned metadata selects KnotClient/KnotServer and exact ASM/Mixin dependencies. Fabric-loader Maven SHA256 d0c5a082e07410aaff9de7ab196aa6b4236002870f9ba3ad5c1260fcce5110ad. Modrinth API metadata gives exact FabricAPI0.165.0+26.3 and Flan26.3-1.12.8.b URLs/sizes/SHA512; LOCK.json records those actual values and original lookup URLs.
- Retained real LSL launcher proof_forest.py327–335 uses Fabric client, real official assets, quickPlayMultiplayer,26.3, offlineUUID, and its source Launch.java only appends accessToken from stdin and calls KnotClient. This candidate uses the same official client entry directly under Linux Xvfb, with accessToken0 only for its fresh loopback offline fixture. No Windows agent, private launcher, profile, server list or session is uploaded.
- Claim JSON derives from the actual native-proven foundation flan_monster_spawn_proof.py364–371 schema: list of admin entries with ID,Name,PosxXzZY,Home,Potions,AllowedEntries,GlobalPerms,PermGroup. This candidate generates ONE own box x16..31/z16..31,default permissions without break permission,randomID,zero player trust. No existing claim/config is copied.
- Actual current official Ubuntu24.04 runner-image documentation at https://github.com/actions/runner-images/blob/main/images/ubuntu/Ubuntu2404-Readme.md lists image20261101.360.1/Ubuntu24.04.5 and xvfb2:21.1.12-1ubuntu1.9. This is image documentation, NOT a runtime graphics proof or guarantee for a future runner. The script requires Xvfb and captures glxinfo when present; then the real client itself decides whether Mesa/libGL/native linking works.

## Resource/time envelope

Manual job only,main-ref/repository-owner actor restriction,contentsread permission,on ubuntu-24.04,JavaTemurin25.0.5+8 (same patch actually observed in prior native CI). Setup actions are the exact commit-pinned actions already used by Root. uv0.10.4 with caches off. No credentials or paid storage/provider call. Python/children inherit nice19. Server1logicalCPU/1GiBheap; client2logicalCPU/2GiBheap; software graphics,800×450,FPS20. OS/renderer memory is additional; no GPU acceleration or RTX performance is claimed.

Preparation600s maximum; native phase600s; bounded server readiness120s/clientjoin180s/individualmarks30–90s inside the native deadline; clean shutdown45+10+10s. Workflow25minutes covers setup/source checks/preparation/native/cleanup. Download failure/slowCDN fails rather than raising the byte/time cap. Only exact owned processes are terminated.

## Genuine compatibility uncertainties that require the hosted run

No Linux Minecraft/Xvfb/GLFW context has been launched for this bundle. Mesa/native-library availability, actual software-OpenGL support, first-run quick-play/onboarding, fresh Fabric server classpath discovery, Flan claim loading and fresh26.3 save-field/compression details still need actual execution. A missing Xvfb/libGL or failed official-client boot is an explicit failure with logs; there is no packet-bot/mock fallback and no automatic unpinned apt install.

The protected leg deliberately requires a real predicted-air DIGHOLD followed by a resynced bone observation. If Flan immediately resyncs before the client ever predicts air, the job reports that unmet bar and fails/inconclusive; it does not silently substitute unchanged-block evidence or another material. The director must decide any revised bar.

Latest source checks:19run,18passed,1Windows file-symlink privilege skip,0failures/errors. The real parent-junction guard test ran successfully. These checks verify only code/metadata/parser properties. First actual hosted run may expose one of these concrete compatibility boundaries. Root should review source/privacy and exact PAYLOAD hash, then run one admitted public job; do not launch a duplicate local client while it runs. No real compatibility blocker is claimed before its measured failure, and no native success is claimed from this preparation.

## Native-directory source contract (revision02)

The exact pinned official26.3 JVM argument is -Djava.library.path=${natives_directory}/java. The driver passes stage/natives as natives_directory, while the downloader extracts Linux native libraries into stage/natives/java. These paths already agree, so no speculative native-path correction was made. The actual source unit resolves the official metadata argument to that nested directory; this is not a Linux linking/OpenGL acceptance result.

Revision02 additionally rejects raw entry/parent symlinks and Windows junctions before resolve(), rejects WSL environment indicators/Microsoft kernels, and restricts the manual workflow to refs/heads/main plus the repository-owner actor. Native judge and expectations are unchanged.
