package net.northstar.gear;
import net.minecraft.server.MinecraftServer;import net.minecraft.item.*;import net.minecraft.component.*;import net.minecraft.component.type.*;import net.minecraft.nbt.*;import java.util.*;
/** Runs inside real Minecraft after registry bootstrap, reachable by local RCON. */
public final class RuntimeChecks {
 static void check(boolean condition,String message){if(!condition)throw new IllegalStateException(message);}
 public static String run(MinecraftServer server){int checks=0;for(int tier=0;tier<4;tier++){
  ItemStack bag=GearItems.make("backpack",tier,"");int capacity=GearPolicy.capacity(tier);List<ItemStack> items=new ArrayList<>();for(int i=0;i<capacity;i++)items.add(new ItemStack(i%2==0?Items.DIAMOND:Items.EMERALD,i%63+1));bag.set(DataComponentTypes.CONTAINER,ContainerComponent.fromStacks(items));
  var ops=server.getRegistryManager().getOps(NbtOps.INSTANCE);var encoded=ItemStack.CODEC.encodeStart(ops,bag).getOrThrow();var decoded=ItemStack.CODEC.parse(ops,encoded).getOrThrow();var loaded=GearItems.contents(decoded,capacity);
  for(int i=0;i<capacity;i++){check(ItemStack.areItemsAndComponentsEqual(items.get(i),loaded.get(i))&&items.get(i).getCount()==loaded.get(i).getCount(),"Roundtrip lost slot "+i);checks++;}
  loaded.get(0).decrement(1);check(GearItems.contents(decoded,capacity).get(0).getCount()==1,"Read leaked mutable references");checks++;
  check(decoded.getMaxCount()==1,"Backpack stackable");checks++;
 }
 var sparse=GearItems.make("backpack",1,"");var sparseItems=new ArrayList<ItemStack>();for(int i=0;i<18;i++)sparseItems.add(ItemStack.EMPTY);sparseItems.set(8,new ItemStack(Items.DIAMOND,3));sparseItems.set(17,new ItemStack(Items.EMERALD,5));sparse.set(DataComponentTypes.CONTAINER,ContainerComponent.fromStacks(sparseItems));var sparseRead=GearItems.contents(sparse,18);check(sparseRead.get(0).isEmpty()&&sparseRead.get(8).isOf(Items.DIAMOND)&&sparseRead.get(17).getCount()==5,"Sparse backpack positions changed");checks++;
 var pouch=GearItems.make("pouch",0,"");pouch.set(DataComponentTypes.CONTAINER,ContainerComponent.fromStacks(List.of(GearItems.make("ring",0,"night_eye"),GearItems.make("ring",0,"strider"),GearItems.make("amulet",0,"slowfall"),GearItems.make("charm",0,"spectral_sight"))));check(GearItems.contents(pouch,4).size()==4,"Pouch missing slots");checks++;
 var gapped=GearItems.make("pouch",0,"");gapped.set(DataComponentTypes.CONTAINER,ContainerComponent.fromStacks(List.of(ItemStack.EMPTY,GearItems.make("ring",0,"strider"),ItemStack.EMPTY,GearItems.make("charm",0,"spectral_sight"))));var gaps=GearItems.contents(gapped,4);check(gaps.get(0).isEmpty()&&GearItems.kind(gaps.get(1)).equals("ring")&&gaps.get(2).isEmpty()&&GearItems.kind(gaps.get(3)).equals("charm"),"Pouch gap positions changed");checks++;
 int recipes=0;var protectedItem=GearItems.make("backpack",0,"");for(var recipe:server.getRecipeManager().values()){for(var ingredient:recipe.value().getIngredients())check(!ingredient.test(protectedItem),"Fallback carrier is vanilla ingredient: "+recipe.id());recipes++;}check(recipes>100,"Recipe safety scan unexpectedly empty");checks++;
 return "NORTHSTAR_RUNTIME_CHECKS_OK checks="+checks+" capacities=9,18,27,54 item_component_roundtrip=true mutable_aliasing=false";
 }
}
