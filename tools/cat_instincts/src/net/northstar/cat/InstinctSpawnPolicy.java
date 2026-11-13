package net.northstar.cat;
/** Exact26.3 source provenance allowlist. Unknown/loaded/managed entities remain unclassified. */
public final class InstinctSpawnPolicy {
    private InstinctSpawnPolicy() { }
    public static boolean naturalWildOrigin(String reason) { return "NATURAL".equals(reason) || "CHUNK_GENERATION".equals(reason); }
}
