package net.northstar.gear;
import net.minecraft.item.*;
import net.minecraft.component.DataComponentTypes;
import net.minecraft.component.type.*;
import net.minecraft.nbt.NbtCompound;
import net.minecraft.text.Text;
import java.util.*;
public final class GearItems {
 public static NbtCompound data(ItemStack s){return s.getOrDefault(DataComponentTypes.CUSTOM_DATA,NbtComponent.DEFAULT).copyNbt();}
 public static String kind(ItemStack s){return data(s).getString("nsp_kind");}
 public static String effect(ItemStack s){return data(s).getString("nsp_effect");}
 public static int tier(ItemStack s){return data(s).getInt("nsp_tier");}
 public static ItemStack make(String kind,int tier,String effect){
  ItemStack s=new ItemStack(Items.RECOVERY_COMPASS);
  s.set(DataComponentTypes.MAX_STACK_SIZE,1);
  NbtCompound n=new NbtCompound();n.putString("nsp_kind",kind);n.putInt("nsp_tier",tier);n.putString("nsp_effect",effect);n.putString("nsp_id",UUID.randomUUID().toString());
  s.set(DataComponentTypes.CUSTOM_DATA,NbtComponent.of(n));
  String label=kind.equals("backpack")?List.of("Leather","Hide","Reinforced","VORATH").get(tier)+" Backpack":kind.equals("pouch")?"Accessory Pouch":effect.replace('_',' ')+" "+kind;
  s.set(DataComponentTypes.CUSTOM_NAME,Text.literal(label));return s;
 }
 public static ItemStack stage(String band,String gem){ItemStack s=make(gem.isEmpty()?"band":"setting",0,"");NbtCompound n=data(s);n.putString("nsp_band",band);n.putString("nsp_gem",gem);s.set(DataComponentTypes.CUSTOM_DATA,NbtComponent.of(n));s.set(DataComponentTypes.CUSTOM_NAME,Text.literal(band+" "+(gem.isEmpty()?"Ring Band":gem+" Setting")));return s;}
 public static ItemStack enchant(ItemStack setting,String effect){ItemStack ring=make("ring",0,effect);NbtCompound n=data(ring),source=data(setting);n.putString("nsp_band",source.getString("nsp_band"));n.putString("nsp_gem",source.getString("nsp_gem"));ring.set(DataComponentTypes.CUSTOM_DATA,NbtComponent.of(n));return ring;}
 public static boolean storage(ItemStack s){return kind(s).equals("backpack")||kind(s).equals("pouch");}
 public static List<ItemStack> contents(ItemStack s,int slots){var list=new ArrayList<ItemStack>();var c=s.getOrDefault(DataComponentTypes.CONTAINER,ContainerComponent.DEFAULT);for(int i=0;i<slots;i++)list.add(ItemStack.EMPTY);var all=net.minecraft.util.collection.DefaultedList.ofSize(slots,ItemStack.EMPTY);c.copyTo(all);for(int i=0;i<slots;i++)list.set(i,all.get(i).copy());return list;}
}
