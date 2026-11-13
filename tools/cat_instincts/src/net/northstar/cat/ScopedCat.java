package net.northstar.cat;

/** Implemented on Cat by its goal mixin; invoked before Mob's first goal-selector tick. */
public interface ScopedCat {
    void northstar$reconcileScope();
}
