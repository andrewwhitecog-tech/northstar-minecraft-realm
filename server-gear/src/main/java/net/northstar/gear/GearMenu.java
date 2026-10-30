package net.northstar.gear;
import eu.pb4.sgui.api.gui.SimpleGui;
import eu.pb4.sgui.api.ClickType;
import net.minecraft.screen.ScreenHandlerType;
import net.minecraft.screen.slot.*;
import net.minecraft.server.network.ServerPlayerEntity;
import net.minecraft.inventory.SimpleInventory;
import net.minecraft.item.ItemStack;
import net.minecraft.component.DataComponentTypes;
import net.minecraft.component.type.ContainerComponent;
import net.minecraft.entity.player.PlayerEntity;
import net.minecraft.text.Text;
import java.util.*;
/** Single server-thread writer. Backing item is locked; mutations write through immediately. */
public final class GearMenu extends SimpleGui {
 public final ItemStack holder; private final int ownerSlot; private final SimpleInventory store; private boolean ready=false,valid=true;
 public GearMenu(ServerPlayerEntity player,int ownerSlot){
  super(type(player.getInventory().getStack(ownerSlot)),player,false);
  this.ownerSlot=ownerSlot;this.holder=player.getInventory().getStack(ownerSlot);
  boolean pouch=GearItems.kind(holder).equals("pouch");int count=pouch?4:GearPolicy.capacity(GearItems.tier(holder));
  store=new SimpleInventory(count){@Override public void markDirty(){super.markDirty();if(ready)persist();}};
  var contents=GearItems.contents(holder,count);for(int i=0;i<count;i++)store.setStack(i,contents.get(i));
  for(int i=0;i<count;i++){final int index=i;setSlotRedirect(i,new Slot(store,i,0,0){
   @Override public boolean canInsert(ItemStack stack){return GearPolicy.accepts(pouch,index,GearItems.kind(stack),GearItems.effect(stack))&&!stack.contains(DataComponentTypes.CONTAINER)&&!stack.contains(DataComponentTypes.BUNDLE_CONTENTS);}
   @Override public int getMaxItemCount(){return pouch?1:64;}
  });}
  setTitle(Text.literal(pouch?"Rings · Rings · Amulet · Charm":"NorthStar Backpack"));ready=true;
 }
 private static ScreenHandlerType<?> type(ItemStack s){if(GearItems.kind(s).equals("pouch"))return ScreenHandlerType.GENERIC_9X1;return switch(GearItems.tier(s)){case 0->ScreenHandlerType.GENERIC_9X1;case 1->ScreenHandlerType.GENERIC_9X2;case 2->ScreenHandlerType.GENERIC_9X3;default->ScreenHandlerType.GENERIC_9X6;};}
 private boolean ownsHolder(){if(!valid)return false;if(holder.isEmpty()||!player.isAlive()||player.isRemoved()||player.getInventory().getStack(ownerSlot)!=holder){valid=false;return false;}return true;}
 private void persist(){if(!ownsHolder())return;var list=new ArrayList<ItemStack>();for(int i=0;i<store.size();i++)list.add(store.getStack(i).copy());holder.set(DataComponentTypes.CONTAINER,ContainerComponent.fromStacks(list));player.getInventory().markDirty();}
 @Override public boolean onAnyClick(int index,ClickType click,SlotActionType action){
  if(!ownsHolder()){close();return false;}Slot slot=getSlotRedirectOrPlayer(index);boolean holderSlot=slot!=null&&slot.inventory==player.getInventory()&&slot.getIndex()==ownerSlot;
  return GearPolicy.actionAllowed(action.name(),holderSlot);
 }
 @Override public ItemStack quickMove(int index){if(!ownsHolder())return ItemStack.EMPTY;Slot slot=getSlotRedirectOrPlayer(index);if(slot!=null&&slot.getStack()==holder)return ItemStack.EMPTY;return super.quickMove(index);}
 @Override public void onTick(){if(!ownsHolder())close();}
 @Override public void onClose(){persist();}
}
