package net.northstar.cat;

import net.fabricmc.api.ModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Explicit opt-in isolated server add-on. No spawn, world edit, permission or pet conversion. */
public final class CatInstincts implements ModInitializer {
    public static final String ENABLE_PROPERTY = "nsp.cat.instincts.enabled";
    public static final Logger LOG = LoggerFactory.getLogger("northstar_cat_instincts");
    public static boolean enabled() { return Boolean.getBoolean(ENABLE_PROPERTY); }
    @Override public void onInitialize() {
        LOG.info("NSP_CAT_INSTINCTS loaded; enabled={}; players/pets/NPCs protected; native acceptance separate", enabled());
    }
}
