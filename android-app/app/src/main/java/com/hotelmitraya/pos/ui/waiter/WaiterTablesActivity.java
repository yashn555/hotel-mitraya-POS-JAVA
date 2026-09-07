package com.hotelmitraya.pos.ui.waiter;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout;
import com.hotelmitraya.pos.HotelMitrayaApp;
import com.hotelmitraya.pos.R;
import com.hotelmitraya.pos.adapter.TableAdapter;
import com.hotelmitraya.pos.api.ApiClient;
import com.hotelmitraya.pos.model.ApiResponse;
import com.hotelmitraya.pos.model.DiningTableModel;
import com.hotelmitraya.pos.ui.auth.LoginActivity;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.List;
import java.util.Map;

public class WaiterTablesActivity extends AppCompatActivity {

    private SwipeRefreshLayout swipeRefresh;
    private TableAdapter tableAdapter;
    private TextView tvWaiterName, tvOccupancyBadge;
    private Button btnFilterAll, btnFilterVacant, btnFilterOccupied;
    private List<DiningTableModel> cachedTables = new java.util.ArrayList<>();
    private String currentFilter = "ALL";

    private final Handler pollHandler = new Handler(Looper.getMainLooper());
    private Runnable pollRunnable;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiter_tables);

        initViews();
        loadTables();
        setupPolling();
    }

    private void initViews() {
        tvWaiterName = findViewById(R.id.tvWaiterName);
        tvOccupancyBadge = findViewById(R.id.tvOccupancyBadge);
        swipeRefresh = findViewById(R.id.swipeRefresh);
        btnFilterAll = findViewById(R.id.btnFilterAll);
        btnFilterVacant = findViewById(R.id.btnFilterVacant);
        btnFilterOccupied = findViewById(R.id.btnFilterOccupied);

        tvWaiterName.setText("Staff: " + HotelMitrayaApp.getInstance().getSessionManager().getUserName());

        btnFilterAll.setOnClickListener(v -> setFilter("ALL"));
        btnFilterVacant.setOnClickListener(v -> setFilter("VACANT"));
        btnFilterOccupied.setOnClickListener(v -> setFilter("OCCUPIED"));

        ImageButton btnLogout = findViewById(R.id.btnLogout);
        btnLogout.setOnClickListener(v -> {
            HotelMitrayaApp.getInstance().getSessionManager().logout();
            Intent intent = new Intent(this, LoginActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(intent);
            finish();
        });

        RecyclerView rvTables = findViewById(R.id.rvTables);
        rvTables.setLayoutManager(new GridLayoutManager(this, 2));

        tableAdapter = new TableAdapter(this, table -> {
            Intent intent = new Intent(WaiterTablesActivity.this, WaiterOrderActivity.class);
            intent.putExtra("table_number", table.getTableNumber());
            intent.putExtra("is_occupied", table.isOccupied());
            if (table.getOrderId() != null) {
                intent.putExtra("order_id", table.getOrderId());
            }
            startActivity(intent);
        });

        rvTables.setAdapter(tableAdapter);

        swipeRefresh.setOnRefreshListener(this::loadTables);
    }

    private void setFilter(String filter) {
        currentFilter = filter;
        btnFilterAll.setBackgroundResource("ALL".equals(filter) ? R.drawable.bg_chip_role_selected : R.drawable.bg_chip_role_unselected);
        btnFilterAll.setTextColor(androidx.core.content.ContextCompat.getColor(this, "ALL".equals(filter) ? R.color.text_white : R.color.text_secondary));

        btnFilterVacant.setBackgroundResource("VACANT".equals(filter) ? R.drawable.bg_chip_role_selected : R.drawable.bg_chip_role_unselected);
        btnFilterVacant.setTextColor(androidx.core.content.ContextCompat.getColor(this, "VACANT".equals(filter) ? R.color.text_white : R.color.text_secondary));

        btnFilterOccupied.setBackgroundResource("OCCUPIED".equals(filter) ? R.drawable.bg_chip_role_selected : R.drawable.bg_chip_role_unselected);
        btnFilterOccupied.setTextColor(androidx.core.content.ContextCompat.getColor(this, "OCCUPIED".equals(filter) ? R.color.text_white : R.color.text_secondary));

        applyFilter();
    }

    private void applyFilter() {
        if (cachedTables == null) return;
        List<DiningTableModel> filtered = new java.util.ArrayList<>();
        for (DiningTableModel tbl : cachedTables) {
            if ("VACANT".equals(currentFilter) && !tbl.isOccupied()) {
                filtered.add(tbl);
            } else if ("OCCUPIED".equals(currentFilter) && tbl.isOccupied()) {
                filtered.add(tbl);
            } else if ("ALL".equals(currentFilter)) {
                filtered.add(tbl);
            }
        }
        tableAdapter.setTables(filtered);
    }

    private void setupPolling() {
        pollRunnable = new Runnable() {
            @Override
            public void run() {
                loadTables();
                pollHandler.postDelayed(this, 5000);
            }
        };
    }

    @Override
    protected void onResume() {
        super.onResume();
        loadTables();
        pollHandler.postDelayed(pollRunnable, 5000);
    }

    @Override
    protected void onPause() {
        super.onPause();
        pollHandler.removeCallbacks(pollRunnable);
    }

    private void loadTables() {
        ApiClient.getService().getWaiterTables().enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
            @Override
            public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                swipeRefresh.setRefreshing(false);
                if (response.isSuccessful() && response.body() != null && response.body().getTables() != null) {
                    cachedTables = response.body().getTables();

                    long occupiedCount = cachedTables.stream().filter(DiningTableModel::isOccupied).count();
                    long vacantCount = cachedTables.size() - occupiedCount;

                    btnFilterAll.setText("All (" + cachedTables.size() + ")");
                    btnFilterVacant.setText("🟢 (" + vacantCount + ")");
                    btnFilterOccupied.setText("🟠 (" + occupiedCount + ")");

                    tvOccupancyBadge.setText(vacantCount + " Free");
                    applyFilter();
                }
            }

            @Override
            public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {
                swipeRefresh.setRefreshing(false);
            }
        });
    }
}
