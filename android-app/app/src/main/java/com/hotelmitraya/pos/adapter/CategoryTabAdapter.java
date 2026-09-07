package com.hotelmitraya.pos.adapter;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.RecyclerView;
import com.hotelmitraya.pos.R;
import com.hotelmitraya.pos.model.CategoryModel;

import java.util.ArrayList;
import java.util.List;

public class CategoryTabAdapter extends RecyclerView.Adapter<CategoryTabAdapter.CategoryViewHolder> {

    public interface OnCategorySelectListener {
        void onCategorySelected(Long categoryId);
    }

    private final Context context;
    private List<CategoryModel> categories = new ArrayList<>();
    private Long selectedCategoryId = null;
    private final OnCategorySelectListener listener;

    public CategoryTabAdapter(Context context, OnCategorySelectListener listener) {
        this.context = context;
        this.listener = listener;
    }

    public void setCategories(List<CategoryModel> list) {
        this.categories = new ArrayList<>();
        // Add "All Dishes" pseudo-category at the front
        CategoryModel allCat = new CategoryModel();
        this.categories.add(allCat);
        if (list != null) {
            this.categories.addAll(list);
        }
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public CategoryViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        Button btn = new Button(context);
        btn.setLayoutParams(new ViewGroup.MarginLayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        int pad = (int) (12 * context.getResources().getDisplayMetrics().density);
        btn.setPadding(pad, 0, pad, 0);
        btn.setTextSize(12);
        return new CategoryViewHolder(btn);
    }

    @Override
    public void onBindViewHolder(@NonNull CategoryViewHolder holder, int position) {
        CategoryModel cat = categories.get(position);
        Long catId = cat.getId();
        String name = catId == null ? "All Dishes" : cat.getName();
        holder.btn.setText(name);

        boolean isSelected = (selectedCategoryId == null && catId == null) || (selectedCategoryId != null && selectedCategoryId.equals(catId));

        if (isSelected) {
            holder.btn.setBackgroundResource(R.drawable.bg_chip_role_selected);
            holder.btn.setTextColor(ContextCompat.getColor(context, R.color.text_white));
        } else {
            holder.btn.setBackgroundResource(R.drawable.bg_chip_role_unselected);
            holder.btn.setTextColor(ContextCompat.getColor(context, R.color.text_secondary));
        }

        holder.btn.setOnClickListener(v -> {
            selectedCategoryId = catId;
            notifyDataSetChanged();
            if (listener != null) listener.onCategorySelected(catId);
        });
    }

    @Override
    public int getItemCount() {
        return categories.size();
    }

    static class CategoryViewHolder extends RecyclerView.ViewHolder {
        Button btn;
        CategoryViewHolder(@NonNull View itemView) {
            super(itemView);
            btn = (Button) itemView;
        }
    }
}
