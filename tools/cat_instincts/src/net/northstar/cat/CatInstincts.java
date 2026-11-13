package net.northstar.cat;

import net.fabricmc.api.ModInitializer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Explicit opt-in isolated server add-on. No spawn, world edit, permission or pet conversion. */
public final class CatInstincts implements ModInitializer {
    public static final String ENABLE_PROPERTY = "nsp.cat.instincts.enabled";
    public static final Logger LOG = LoggerFactory.getLogger("northstar_cat_instincts");
    public static boolean enabled() { return Boolean.getBoolean(ENABLE_PROPERTY); }
    public static boolean active(net.minecraft.world.entity.animal.feline.Cat cat) {
        return InstinctScope.active(enabled(),cat.level() instanceof net.minecraft.server.level.ServerLevel,
            cat.isTame() && !cat.isBaby(),cat.entityTags());
    }
    @Override public void onInitialize() {
        LOG.info("NSP_CAT_INSTINCTS loaded; enabled={}; explicit canary tag required; players/pets/NPCs protected; native acceptance separate", enabled());
    }
}
