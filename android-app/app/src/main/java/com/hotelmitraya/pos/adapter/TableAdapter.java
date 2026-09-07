package com.hotelmitraya.pos.adapter;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.core.content.ContextCompat;
import androidx.recyclerview.widget.RecyclerView;
import com.hotelmitraya.pos.R;
import com.hotelmitraya.pos.model.DiningTableModel;

import java.util.ArrayList;
import java.util.List;

public class TableAdapter extends RecyclerView.Adapter<TableAdapter.TableViewHolder> {

    public interface OnTableClickListener {
        void onTableClick(DiningTableModel table);
    }

    private final Context context;
    private List<DiningTableModel> tables = new ArrayList<>();
    private final OnTableClickListener listener;

    public TableAdapter(Context context, OnTableClickListener listener) {
        this.context = context;
        this.listener = listener;
    }

    public void setTables(List<DiningTableModel> tables) {
        this.tables = tables != null ? tables : new ArrayList<>();
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public TableViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(context).inflate(R.layout.item_table_card, parent, false);
        return new TableViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull TableViewHolder holder, int position) {
        DiningTableModel table = tables.get(position);
        holder.tvTableNumber.setText("Table " + table.getTableNumber());

        if (table.isOccupied()) {
            holder.tvTableStatus.setText(context.getString(R.string.status_occupied));
            holder.tvTableStatus.setTextColor(ContextCompat.getColor(context, R.color.status_occupied));
            holder.tvTableStatus.setBackgroundResource(R.drawable.bg_badge_occupied);

            holder.layoutActiveOrderInfo.setVisibility(View.VISIBLE);
            holder.tvOrderNumber.setText(table.getOrderNumber() != null ? "Order #" + table.getOrderNumber() : "Active Order");
            holder.tvItemCount.setText(table.getItemsCount() + " Items");
            holder.tvElapsedTime.setText("⏱ " + table.getElapsedMinutes() + "m ago");
            holder.tvOrderAmount.setText(String.format("Total: ₹%.2f", table.getTotalAmount()));

            holder.btnTableAction.setText(context.getString(R.string.edit_order));
        } else {
            holder.tvTableStatus.setText(context.getString(R.string.status_vacant));
            holder.tvTableStatus.setTextColor(ContextCompat.getColor(context, R.color.status_vacant));
            holder.tvTableStatus.setBackgroundResource(R.drawable.bg_badge_vacant);

            holder.layoutActiveOrderInfo.setVisibility(View.GONE);
            holder.btnTableAction.setText(context.getString(R.string.take_order));
        }

        holder.itemView.setOnClickListener(v -> {
            if (listener != null) listener.onTableClick(table);
        });

        holder.btnTableAction.setOnClickListener(v -> {
            if (listener != null) listener.onTableClick(table);
        });
    }

    @Override
    public int getItemCount() {
        return tables.size();
    }

    static class TableViewHolder extends RecyclerView.ViewHolder {
        TextView tvTableNumber, tvTableStatus, tvOrderNumber, tvItemCount, tvElapsedTime, tvOrderAmount;
        LinearLayout layoutActiveOrderInfo;
        Button btnTableAction;

        TableViewHolder(@NonNull View itemView) {
            super(itemView);
            tvTableNumber = itemView.findViewById(R.id.tvTableNumber);
            tvTableStatus = itemView.findViewById(R.id.tvTableStatus);
            tvOrderNumber = itemView.findViewById(R.id.tvOrderNumber);
            tvItemCount = itemView.findViewById(R.id.tvItemCount);
            tvElapsedTime = itemView.findViewById(R.id.tvElapsedTime);
            tvOrderAmount = itemView.findViewById(R.id.tvOrderAmount);
            layoutActiveOrderInfo = itemView.findViewById(R.id.layoutActiveOrderInfo);
            btnTableAction = itemView.findViewById(R.id.btnTableAction);
        }
    }
}
