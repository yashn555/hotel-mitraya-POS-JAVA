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
import com.hotelmitraya.pos.model.PosBillModel;

import java.util.ArrayList;
import java.util.List;

public class BillHistoryAdapter extends RecyclerView.Adapter<BillHistoryAdapter.BillViewHolder> {

    public interface OnReprintClickListener {
        void onReprint(PosBillModel bill);
    }

    private final Context context;
    private List<PosBillModel> bills = new ArrayList<>();
    private final OnReprintClickListener listener;

    public BillHistoryAdapter(Context context, OnReprintClickListener listener) {
        this.context = context;
        this.listener = listener;
    }

    public void setBills(List<PosBillModel> list) {
        this.bills = list != null ? list : new ArrayList<>();
        notifyDataSetChanged();
    }

    @NonNull
    @Override
    public BillViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        View view = LayoutInflater.from(context).inflate(R.layout.item_bill_history, parent, false);
        return new BillViewHolder(view);
    }

    @Override
    public void onBindViewHolder(@NonNull BillViewHolder holder, int position) {
        PosBillModel bill = bills.get(position);
        holder.tvHistoryBillNo.setText(bill.getBillNumber());
        holder.tvHistoryTable.setText(bill.getTableLabel());
        holder.tvHistoryCustomer.setText(bill.getCustomerName().isEmpty() ? "Customer: Walk-in" : "Customer: " + bill.getCustomerName());
        holder.tvHistoryDate.setText(bill.getCreatedAt() != null ? bill.getCreatedAt() : "");
        holder.tvHistoryAmount.setText(String.format("₹%.2f", bill.getTotalAmount()));

        holder.btnReprint.setOnClickListener(v -> {
            if (listener != null) listener.onReprint(bill);
        });
    }

    @Override
    public int getItemCount() {
        return bills.size();
    }

    static class BillViewHolder extends RecyclerView.ViewHolder {
        TextView tvHistoryBillNo, tvHistoryTable, tvHistoryCustomer, tvHistoryDate, tvHistoryAmount;
        Button btnReprint;

        BillViewHolder(@NonNull View itemView) {
            super(itemView);
            tvHistoryBillNo = itemView.findViewById(R.id.tvHistoryBillNo);
            tvHistoryTable = itemView.findViewById(R.id.tvHistoryTable);
            tvHistoryCustomer = itemView.findViewById(R.id.tvHistoryCustomer);
            tvHistoryDate = itemView.findViewById(R.id.tvHistoryDate);
            tvHistoryAmount = itemView.findViewById(R.id.tvHistoryAmount);
            btnReprint = itemView.findViewById(R.id.btnReprint);
        }
    }
}
