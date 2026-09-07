package com.hotelmitraya.pos.ui.kitchen;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.hotelmitraya.pos.R;
import com.hotelmitraya.pos.api.ApiClient;
import com.hotelmitraya.pos.model.ApiResponse;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.*;

public class KitchenDisplayActivity extends AppCompatActivity {

    private SwipeRefreshLayout swipeRefresh;
    private RecyclerView rvTickets;
    private TextView tvActiveTicketsCount;
    private KitchenTicketAdapter adapter;

    private final Handler pollHandler = new Handler(Looper.getMainLooper());
    private Runnable pollRunnable;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_kitchen_display);

        initViews();
        loadTickets();
        setupPolling();
    }

    private void initViews() {
        tvActiveTicketsCount = findViewById(R.id.tvActiveTicketsCount);
        swipeRefresh = findViewById(R.id.swipeRefreshKds);
        rvTickets = findViewById(R.id.rvKitchenTickets);

        rvTickets.setLayoutManager(new LinearLayoutManager(this));
        adapter = new KitchenTicketAdapter(this::markOrderReady);
        rvTickets.setAdapter(adapter);

        swipeRefresh.setOnRefreshListener(this::loadTickets);
    }

    private void setupPolling() {
        pollRunnable = new Runnable() {
            @Override
            public void run() {
                loadTickets();
                pollHandler.postDelayed(this, 5000);
            }
        };
    }

    @Override
    protected void onResume() {
        super.onResume();
        loadTickets();
        pollHandler.postDelayed(pollRunnable, 5000);
    }

    @Override
    protected void onPause() {
        super.onPause();
        pollHandler.removeCallbacks(pollRunnable);
    }

    private void loadTickets() {
        ApiClient.getService().getKitchenOrders().enqueue(new Callback<Map<String, Object>>() {
            @Override
            public void onResponse(Call<Map<String, Object>> call, Response<Map<String, Object>> response) {
                swipeRefresh.setRefreshing(false);
                if (response.isSuccessful() && response.body() != null) {
                    @SuppressWarnings("unchecked")
                    List<Map<String, Object>> orders = (List<Map<String, Object>>) response.body().get("orders");
                    if (orders != null) {
                        adapter.setTickets(orders);
                        tvActiveTicketsCount.setText(orders.size() + " Orders Live");
                    }
                }
            }

            @Override
            public void onFailure(Call<Map<String, Object>> call, Throwable t) {
                swipeRefresh.setRefreshing(false);
            }
        });
    }

    private void markOrderReady(Long orderId) {
        Map<String, Object> body = new HashMap<>();
        body.put("status", "READY");

        ApiClient.getService().updateOrderStatus(orderId, body).enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
            @Override
            public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                Toast.makeText(KitchenDisplayActivity.this, "Order marked READY!", Toast.LENGTH_SHORT).show();
                loadTickets();
            }

            @Override
            public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {
                Toast.makeText(KitchenDisplayActivity.this, "Failed to update status", Toast.LENGTH_SHORT).show();
            }
        });
    }

    static class KitchenTicketAdapter extends RecyclerView.Adapter<KitchenTicketAdapter.TicketViewHolder> {

        interface OnReadyClickListener {
            void onReady(Long orderId);
        }

        private List<Map<String, Object>> tickets = new ArrayList<>();
        private final OnReadyClickListener listener;

        KitchenTicketAdapter(OnReadyClickListener listener) {
            this.listener = listener;
        }

        void setTickets(List<Map<String, Object>> list) {
            this.tickets = list != null ? list : new ArrayList<>();
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public TicketViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            View view = LayoutInflater.from(parent.getContext()).inflate(R.layout.item_kitchen_ticket, parent, false);
            return new TicketViewHolder(view);
        }

        @Override
        public void onBindViewHolder(@NonNull TicketViewHolder holder, int position) {
            Map<String, Object> ticket = tickets.get(position);
            holder.tvTicketTable.setText(String.valueOf(ticket.getOrDefault("table_label", "Table")));
            holder.tvTicketOrderNumber.setText("Order #" + ticket.getOrDefault("order_number", ""));
            holder.tvTicketElapsed.setText("⏱ " + ticket.getOrDefault("elapsed_minutes", 0) + "m ago");

            holder.layoutDishes.removeAllViews();
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> items = (List<Map<String, Object>>) ticket.get("items");
            if (items != null) {
                for (Map<String, Object> item : items) {
                    TextView tv = new TextView(holder.itemView.getContext());
                    tv.setText(item.get("quantity") + "x  " + item.get("item_name"));
                    tv.setTextColor(holder.itemView.getContext().getColor(R.color.text_primary));
                    tv.setTextSize(15);
                    tv.setPadding(0, 4, 0, 4);
                    holder.layoutDishes.addView(tv);
                }
            }

            String notes = String.valueOf(ticket.getOrDefault("notes", "")).trim();
            if (!notes.isEmpty()) {
                holder.tvTicketNotes.setVisibility(View.VISIBLE);
                holder.tvTicketNotes.setText("Note: " + notes);
            } else {
                holder.tvTicketNotes.setVisibility(View.GONE);
            }

            holder.btnMarkReady.setOnClickListener(v -> {
                if (listener != null && ticket.get("id") != null) {
                    long oid = ((Number) ticket.get("id")).longValue();
                    listener.onReady(oid);
                }
            });
        }

        @Override
        public int getItemCount() {
            return tickets.size();
        }

        static class TicketViewHolder extends RecyclerView.ViewHolder {
            TextView tvTicketTable, tvTicketOrderNumber, tvTicketElapsed, tvTicketNotes;
            LinearLayout layoutDishes;
            Button btnMarkReady;

            TicketViewHolder(@NonNull View itemView) {
                super(itemView);
                tvTicketTable = itemView.findViewById(R.id.tvTicketTable);
                tvTicketOrderNumber = itemView.findViewById(R.id.tvTicketOrderNumber);
                tvTicketElapsed = itemView.findViewById(R.id.tvTicketElapsed);
                tvTicketNotes = itemView.findViewById(R.id.tvTicketNotes);
                layoutDishes = itemView.findViewById(R.id.layoutTicketDishes);
                btnMarkReady = itemView.findViewById(R.id.btnMarkReady);
            }
        }
    }
}
