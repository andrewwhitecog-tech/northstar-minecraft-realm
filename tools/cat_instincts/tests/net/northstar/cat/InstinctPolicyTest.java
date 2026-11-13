package net.northstar.cat;

import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Actual policy regressions for the same decision functions used at contact. Runtime proof separate. */
public class InstinctPolicyTest {
    private InstinctPolicy.Contact contact(boolean player,boolean owner,boolean pet,boolean npc,
            boolean allied,boolean protectedTag,boolean playable,boolean hostile,boolean wild) {
        return new InstinctPolicy.Contact(true,true,false,true,true,player,owner,pet,npc,allied,protectedTag,playable,hostile,wild);
    }
    @Test void hostileAndWildPreyAreProactivePositiveCases() {
        assertTrue(InstinctPolicy.mayDamage(contact(false,false,false,false,false,false,false,true,false)));
        assertTrue(InstinctPolicy.mayDamage(contact(false,false,false,false,false,false,false,false,true)));
        assertFalse(InstinctPolicy.mayDamage(contact(false,false,false,false,false,false,false,false,false)));
    }
    @Test void playerAndOwnerNeverBecomeAttackableEvenWhenFlaggedHostile() {
        assertFalse(InstinctPolicy.mayDamage(contact(true,false,false,false,false,false,false,true,true)));
        assertFalse(InstinctPolicy.mayDamage(contact(false,true,false,false,false,false,false,true,true)));
        assertEquals(InstinctPolicy.Relation.PROTECTED,InstinctPolicy.relation(contact(true,false,false,false,false,false,true,true,true)));
    }
    @Test void EveryPetNpcAllyAndProtectedAnimalVetoesDamage() {
        for (int kind=0;kind<4;kind++) {
            var c=contact(false,false,kind==0,kind==1,kind==2,kind==3,false,true,true);
            assertFalse(InstinctPolicy.mayDamage(c),"Protection must win over hostile/wild classification");
        }
    }
    @Test void PetAndManagedAnimalPlayIsHarmlessAndNpcIsNotAPlaymate() {
        for (var c : new InstinctPolicy.Contact[]{
                contact(false,false,true,false,false,false,true,true,true),
                contact(false,false,false,false,false,true,true,false,false),
                contact(false,false,false,false,true,false,true,false,false)}) {
            assertEquals(InstinctPolicy.Relation.PLAYMATE,InstinctPolicy.relation(c));
            assertFalse(InstinctPolicy.mayDamage(c));
        }
        assertEquals(InstinctPolicy.Relation.PROTECTED,InstinctPolicy.relation(contact(false,false,false,true,false,false,true,true,true)));
    }
    @Test void ProtectionAddedBetweenAcquisitionAndContactStopsThePreviouslyValidAttack() {
        var acquired=contact(false,false,false,false,false,false,false,true,false);
        var atContact=contact(false,false,false,false,false,true,false,true,false);
        assertTrue(InstinctPolicy.mayDamage(acquired));
        assertFalse(InstinctPolicy.mayDamage(atContact));
    }
    @Test void TamingBetweenAcquisitionAndContactProtectsTheNewPet() {
        assertTrue(InstinctPolicy.mayDamage(contact(false,false,false,false,false,false,false,false,true)));
        assertFalse(InstinctPolicy.mayDamage(contact(false,false,true,false,false,false,true,false,true)));
    }
    @Test void DisabledUntamedCrossWorldDeadAndSittingCasesFailClosed() {
        var cases=new InstinctPolicy.Contact[]{
            new InstinctPolicy.Contact(false,true,false,true,true,false,false,false,false,false,false,false,true,true),
            new InstinctPolicy.Contact(true,false,false,true,true,false,false,false,false,false,false,false,true,true),
            new InstinctPolicy.Contact(true,true,false,false,true,false,false,false,false,false,false,false,true,true),
            new InstinctPolicy.Contact(true,true,false,true,false,false,false,false,false,false,false,false,true,true),
            new InstinctPolicy.Contact(true,true,true,true,true,false,false,false,false,false,false,false,true,true)};
        for (var c:cases) assertFalse(InstinctPolicy.mayDamage(c));
    }
}
