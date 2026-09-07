package com.hotelmitraya.pos.adapter;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;
import com.hotelmitraya.pos.R;
import com.hotelmitraya.pos.model.MenuItemModel;

import java.util.ArrayList;
import java.util.List;

public class MenuItemAdapter extends RecyclerView.Adapter<MenuItemAdapter.MenuViewHolder> {

    public interface OnQuantityChangeListener {
        void onQuantityChanged(MenuItemModel item, int newQty);
    }

    private final Context context;
    private List<MenuItemModel> allItems = new ArrayList<>();
    private List<MenuItemModel> displayedItems = new ArrayList<>();
    private final OnQuantityChangeListener listener;

    public MenuItemAdapter(Context context, OnQuantityChangeListener listener) {
        this.context = context;
        this.listener = listener;
    }

    public void setItems(List<MenuItemModel> list) {
        this.allItems = list != null ? list : new ArrayList<>();
        this.displayedItems = new ArrayList<>(this.allItems);
        notifyDataSetChanged();
    }

    public void filter(Long categoryId, String searchQuery) {
        displayedItems.clear();
        String query = searchQuery != null ? searchQuery.toLowerCase().trim() : "";

        for (MenuItemModel item : allItems) {
            boolean matchesCat = categoryId == null || categoryId.equals(item.getCategoryId());
            boolean matchesQuery = query.isEmpty() ||
                    item.getName().toLowerCase().contains(query) ||
                    item.getCode().toLowerCase().contains(query);

            if (matchesCat && matchesQuery) {
                displayedItems.add(item);
            }
        }
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public MenuViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(context).inflate(R.layout.item_menu_dish, parent, false);
        return new MenuViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull MenuViewHolder holder, int position) {
        MenuItemModel item = displayedItems.get(position);
        holder.tvDishName.setText(item.getName());
        holder.tvDishPrice.setText(String.format("₹%.2f", item.getPrice()));
        holder.tvDishCode.setText(!item.getCode().isEmpty() ? item.getCode() : "");
        holder.tvQuantity.setText(String.valueOf(item.getSelectedQuantity()));

        // Veg / Non-Veg badge
        holder.ivVegBadge.setImageResource(item.isVeg() ? R.drawable.ic_veg : R.drawable.ic_nonveg);

        // Highlight card if selected
        if (item.getSelectedQuantity() > 0) {
            holder.cardDish.setCardBackgroundColor(androidx.core.content.ContextCompat.getColor(context, R.color.bg_card_active));
            holder.cardDish.setStrokeColor(androidx.core.content.ContextCompat.getColor(context, R.color.brand_accent));
            holder.cardDish.setStrokeWidth(2);
        } else {
            holder.cardDish.setCardBackgroundColor(androidx.core.content.ContextCompat.getColor(context, R.color.bg_surface));
            holder.cardDish.setStrokeColor(androidx.core.content.ContextCompat.getColor(context, R.color.card_border));
            holder.cardDish.setStrokeWidth(1);
        }

        holder.btnPlus.setOnClickListener(v -> {
            int newQty = item.getSelectedQuantity() + 1;
            item.setSelectedQuantity(newQty);
            holder.tvQuantity.setText(String.valueOf(newQty));
            notifyItemChanged(position);
            if (listener != null) listener.onQuantityChanged(item, newQty);
        });

        holder.btnMinus.setOnClickListener(v -> {
            if (item.getSelectedQuantity() > 0) {
                int newQty = item.getSelectedQuantity() - 1;
                item.setSelectedQuantity(newQty);
                holder.tvQuantity.setText(String.valueOf(newQty));
                notifyItemChanged(position);
                if (listener != null) listener.onQuantityChanged(item, newQty);
            }
        });
    }

    @Override
    public int getItemCount() {
        return displayedItems.size();
    }

    static class MenuViewHolder extends RecyclerView.ViewHolder {
        com.google.android.material.card.MaterialCardView cardDish;
        android.widget.ImageView ivVegBadge;
        TextView tvDishName, tvDishPrice, tvDishCode, tvQuantity;
        Button btnMinus, btnPlus;

        MenuViewHolder(@NonNull View itemView) {
            super(itemView);
            cardDish = itemView.findViewById(R.id.cardDish);
            ivVegBadge = itemView.findViewById(R.id.ivVegBadge);
            tvDishName = itemView.findViewById(R.id.tvDishName);
            tvDishPrice = itemView.findViewById(R.id.tvDishPrice);
            tvDishCode = itemView.findViewById(R.id.tvDishCode);
            tvQuantity = itemView.findViewById(R.id.tvQuantity);
            btnMinus = itemView.findViewById(R.id.btnMinus);
            btnPlus = itemView.findViewById(R.id.btnPlus);
        }
    }
}
