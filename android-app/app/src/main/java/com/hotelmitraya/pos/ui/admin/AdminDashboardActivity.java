package com.hotelmitraya.pos.ui.admin;

import android.content.Intent;
import android.os.Bundle;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.ImageButton;
import android.widget.TextView;
import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.hotelmitraya.pos.HotelMitrayaApp;
import com.hotelmitraya.pos.R;
import com.hotelmitraya.pos.api.ApiClient;
import com.hotelmitraya.pos.model.ApiResponse;
import com.hotelmitraya.pos.ui.auth.LoginActivity;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.*;

public class AdminDashboardActivity extends AppCompatActivity {

    private TextView tvAdminTotalSales, tvAdminBillsCount, tvAdminCashSales, tvAdminUpiSales, tvAdminCardSales;
    private BestSellerAdapter bestSellerAdapter;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_admin_dashboard);

        initViews();
        loadAnalytics();
    }

    private void initViews() {
        tvAdminTotalSales = findViewById(R.id.tvAdminTotalSales);
        tvAdminBillsCount = findViewById(R.id.tvAdminBillsCount);
        tvAdminCashSales = findViewById(R.id.tvAdminCashSales);
        tvAdminUpiSales = findViewById(R.id.tvAdminUpiSales);
        tvAdminCardSales = findViewById(R.id.tvAdminCardSales);

        ImageButton btnLogout = findViewById(R.id.btnAdminLogout);
        btnLogout.setOnClickListener(v -> {
            HotelMitrayaApp.getInstance().getSessionManager().logout();
            Intent intent = new Intent(this, LoginActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(intent);
            finish();
        });

        RecyclerView rvBest = findViewById(R.id.rvBestSellers);
        rvBest.setLayoutManager(new LinearLayoutManager(this));
        bestSellerAdapter = new BestSellerAdapter();
        rvBest.setAdapter(bestSellerAdapter);
    }

    private void loadAnalytics() {
        ApiClient.getService().getSalesSummary().enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
            @Override
            public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                if (response.isSuccessful() && response.body() != null) {
                    // Load sales numbers
                }
            }
            @Override
            public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {}
        });

        ApiClient.getService().getBestSellers(10).enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
            @Override
            public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                // Populate best sellers
            }
            @Override
            public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {}
        });
    }

    static class BestSellerAdapter extends RecyclerView.Adapter<BestSellerAdapter.ViewHolder> {
        private List<Map<String, Object>> items = new ArrayList<>();

        void setItems(List<Map<String, Object>> list) {
            this.items = list != null ? list : new ArrayList<>();
            notifyDataSetChanged();
        }

        @NonNull
        @Override
        public ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
            TextView tv = new TextView(parent.getContext());
            tv.setPadding(16, 12, 16, 12);
            tv.setTextColor(parent.getContext().getColor(R.color.text_primary));
            tv.setTextSize(14);
            return new ViewHolder(tv);
        }

        @Override
        public void onBindViewHolder(@NonNull ViewHolder holder, int position) {
            Map<String, Object> itm = items.get(position);
            holder.tv.setText((position + 1) + ". " + itm.get("item_name") + " (" + itm.get("total_qty") + " sold - ₹" + itm.get("total_revenue") + ")");
        }

        @Override
        public int getItemCount() {
            return items.size();
        }

        static class ViewHolder extends RecyclerView.ViewHolder {
            TextView tv;
            ViewHolder(View itemView) { super(itemView); tv = (TextView) itemView; }
        }
    }
}
