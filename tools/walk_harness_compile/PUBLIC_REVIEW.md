# Public export review

Allowlisted source: RouteWalk.java frozen v02 fail-closed; unchanged FrameRecorder.java; unchanged MinecraftFrameMixin.java. Their exact SHA-256 values are in the manifest. Actual sources were read before export. No private player names/UUIDs, fixture coordinates, server endpoints, world paths, login material, tokens or workstation drive paths are present in their runtime code. The unchanged recorder documentation contains a generic first-name reference to the owner's screen; it is not a player identifier or credential and no identity is bound at runtime. Root reviews the final public diff before publication.

Resources: fabric.mod.json and nsp_route_walk.mixins.json were extracted from the exact pinned shared harness JAR (SHA-256 4ccbc478aaa649a74cc182ca19038b44b02bbd01f658c62f19f8b8ab3e6be50b), individually read and hashed, and copied unchanged. Their contents declare only the public mod/package/Java/Minecraft/Fabric entrypoint contract.

Dependency manifest: ordered logical artifact IDs, Maven coordinates, public HTTPS download locations, published digests/sizes, public metadata provenance and observed verification times. All original workstation locations are excluded. Publisher artifacts are downloaded only by an explicitly opted-in genuine hosted Linux GitHub job into ephemeral build/. This payload contains no third-party dependency binaries and grants no additional Minecraft redistribution rights.

Driver: validate-only by default; rejects local/Windows/WSL/self-hosted compilation; no provider call, shell command string, local JVM invocation, workflow publishing, artifact storage or cache storage. In CI it compiles and packages only the harness namespace/resources. Its bounded base64 delivery includes only that own-code candidate JAR and never environment values or tokens.

Status: SOURCE_PAYLOAD_ONLY. Official download metadata was verified; no local JVM, cloud job, compiled JAR or native proof was run by this preparation task. Root owns workflow publication, actual CI execution, downloaded-log reconstruction, owner review and any later controlled native integration.
