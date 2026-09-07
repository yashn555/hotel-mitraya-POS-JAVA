package com.hotelmitraya.pos.ui.pos;

import android.content.Intent;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.widget.*;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.GridLayoutManager;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.google.android.material.tabs.TabLayout;
import com.hotelmitraya.pos.HotelMitrayaApp;
import com.hotelmitraya.pos.R;
import com.hotelmitraya.pos.adapter.BillHistoryAdapter;
import com.hotelmitraya.pos.adapter.MenuItemAdapter;
import com.hotelmitraya.pos.adapter.TableAdapter;
import com.hotelmitraya.pos.api.ApiClient;
import com.hotelmitraya.pos.model.*;
import com.hotelmitraya.pos.ui.auth.LoginActivity;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.*;

public class PosCounterActivity extends AppCompatActivity {

    private View viewWalkInBilling, viewDiningSettle, viewRecentBills;
    private MenuItemAdapter walkInMenuAdapter;
    private TableAdapter diningTableAdapter;
    private BillHistoryAdapter billHistoryAdapter;

    private List<MenuItemModel> walkInDishes = new ArrayList<>();
    private EditText etCustomerName, etDiscount, etReceivedAmount;
    private TextView tvPosGrandTotal, tvChangeAmount, tvCashierName;
    private RadioGroup rgPaymentMode;
    private Button btnPosCheckout;

    private double walkInSubtotal = 0.0;
    private double walkInDiscount = 0.0;
    private double walkInGrandTotal = 0.0;
    private String paymentMode = "CASH";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_pos_counter);

        initViews();
        setupTabs();
        loadWalkInCatalog();
        loadDiningTables();
        loadRecentBills();
    }

    private void initViews() {
        tvCashierName = findViewById(R.id.tvCashierName);
        tvCashierName.setText("Cashier: " + HotelMitrayaApp.getInstance().getSessionManager().getUserName());

        ImageButton btnLogout = findViewById(R.id.btnPosLogout);
        btnLogout.setOnClickListener(v -> {
            HotelMitrayaApp.getInstance().getSessionManager().logout();
            Intent intent = new Intent(this, LoginActivity.class);
            intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
            startActivity(intent);
            finish();
        });

        viewWalkInBilling = findViewById(R.id.viewWalkInBilling);
        viewDiningSettle = findViewById(R.id.viewDiningSettle);
        viewRecentBills = findViewById(R.id.viewRecentBills);

        etCustomerName = findViewById(R.id.etCustomerName);
        etDiscount = findViewById(R.id.etDiscount);
        etReceivedAmount = findViewById(R.id.etReceivedAmount);
        tvPosGrandTotal = findViewById(R.id.tvPosGrandTotal);
        tvChangeAmount = findViewById(R.id.tvChangeAmount);
        rgPaymentMode = findViewById(R.id.rgPaymentMode);
        btnPosCheckout = findViewById(R.id.btnPosCheckout);

        // Walk-in Menu RecyclerView
        RecyclerView rvWalkIn = findViewById(R.id.rvWalkInMenu);
        rvWalkIn.setLayoutManager(new LinearLayoutManager(this));
        walkInMenuAdapter = new MenuItemAdapter(this, (item, newQty) -> recalculateWalkIn());
        rvWalkIn.setAdapter(walkInMenuAdapter);

        // Dining Tables RecyclerView
        RecyclerView rvDining = findViewById(R.id.rvDiningTablesSettle);
        rvDining.setLayoutManager(new GridLayoutManager(this, 2));
        diningTableAdapter = new TableAdapter(this, table -> {
            if (table.isOccupied()) {
                TableSettleDialog dialog = new TableSettleDialog(this, table, this::loadDiningTables);
                dialog.show();
            } else {
                Toast.makeText(this, "Table " + table.getTableNumber() + " is currently Vacant.", Toast.LENGTH_SHORT).show();
            }
        });
        rvDining.setAdapter(diningTableAdapter);

        // Recent Bills RecyclerView
        RecyclerView rvRecent = findViewById(R.id.rvRecentBills);
        rvRecent.setLayoutManager(new LinearLayoutManager(this));
        billHistoryAdapter = new BillHistoryAdapter(this, bill -> reprintBill(bill.getId()));
        rvRecent.setAdapter(billHistoryAdapter);

        // Payment Mode toggle
        rgPaymentMode.setOnCheckedChangeListener((group, checkedId) -> {
            if (checkedId == R.id.rbCash) {
                paymentMode = "CASH";
                findViewById(R.id.layoutCashChange).setVisibility(View.VISIBLE);
            } else if (checkedId == R.id.rbUpi) {
                paymentMode = "UPI";
                findViewById(R.id.layoutCashChange).setVisibility(View.GONE);
            } else {
                paymentMode = "CARD";
                findViewById(R.id.layoutCashChange).setVisibility(View.GONE);
            }
        });

        etDiscount.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                try {
                    walkInDiscount = Double.parseDouble(s.toString().trim());
                } catch (Exception e) {
                    walkInDiscount = 0.0;
                }
                updateWalkInTotals();
            }
            @Override
            public void afterTextChanged(Editable s) {}
        });

        etReceivedAmount.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                updateWalkInChange();
            }
            @Override
            public void afterTextChanged(Editable s) {}
        });

        btnPosCheckout.setOnClickListener(v -> performWalkInCheckout());
    }

    private void setupTabs() {
        TabLayout tabLayout = findViewById(R.id.tabLayoutPos);
        tabLayout.addOnTabSelectedListener(new TabLayout.OnTabSelectedListener() {
            @Override
            public void onTabSelected(TabLayout.Tab tab) {
                viewWalkInBilling.setVisibility(tab.getPosition() == 0 ? View.VISIBLE : View.GONE);
                viewDiningSettle.setVisibility(tab.getPosition() == 1 ? View.VISIBLE : View.GONE);
                viewRecentBills.setVisibility(tab.getPosition() == 2 ? View.VISIBLE : View.GONE);

                if (tab.getPosition() == 1) loadDiningTables();
                if (tab.getPosition() == 2) loadRecentBills();
            }
            @Override
            public void onTabUnselected(TabLayout.Tab tab) {}
            @Override
            public void onTabReselected(TabLayout.Tab tab) {}
        });
    }

    private void loadWalkInCatalog() {
        ApiClient.getService().getPosCatalog().enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
            @Override
            public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                if (response.isSuccessful() && response.body() != null && response.body().getCategories() != null) {
                    walkInDishes.clear();
                    for (CategoryModel cat : response.body().getCategories()) {
                        if (cat.getItems() != null) {
                            walkInDishes.addAll(cat.getItems());
                        }
                    }
                    walkInMenuAdapter.setItems(walkInDishes);
                }
            }
            @Override
            public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {}
        });
    }

    private void loadDiningTables() {
        ApiClient.getService().getPosTables().enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
            @Override
            public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                if (response.isSuccessful() && response.body() != null && response.body().getTables() != null) {
                    diningTableAdapter.setTables(response.body().getTables());
                }
            }
            @Override
            public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {}
        });
    }

    private void loadRecentBills() {
        ApiClient.getService().getRecentBills(30).enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
            @Override
            public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                if (response.isSuccessful() && response.body() != null && response.body().getBills() != null) {
                    billHistoryAdapter.setBills(response.body().getBills());
                }
            }
            @Override
            public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {}
        });
    }

    private void recalculateWalkIn() {
        walkInSubtotal = 0.0;
        for (MenuItemModel item : walkInDishes) {
            if (item.getSelectedQuantity() > 0) {
                walkInSubtotal += (item.getSelectedQuantity() * item.getPrice());
            }
        }
        updateWalkInTotals();
    }

    private void updateWalkInTotals() {
        walkInDiscount = Math.min(walkInDiscount, walkInSubtotal);
        walkInGrandTotal = Math.max(0.0, walkInSubtotal - walkInDiscount);
        tvPosGrandTotal.setText(String.format("Grand Total: ₹%.2f", walkInGrandTotal));
        updateWalkInChange();
    }

    private void updateWalkInChange() {
        try {
            double rec = Double.parseDouble(etReceivedAmount.getText().toString().trim());
            double change = Math.max(0.0, rec - walkInGrandTotal);
            tvChangeAmount.setText(String.format("Change: ₹%.2f", change));
        } catch (Exception e) {
            tvChangeAmount.setText("Change: ₹0.00");
        }
    }

    private void performWalkInCheckout() {
        List<Map<String, Object>> cartItems = new ArrayList<>();
        for (MenuItemModel item : walkInDishes) {
            if (item.getSelectedQuantity() > 0) {
                Map<String, Object> itm = new HashMap<>();
                itm.put("menu_item_id", item.getId());
                itm.put("name", item.getName());
                itm.put("quantity", item.getSelectedQuantity());
                itm.put("unit_price", item.getPrice());
                cartItems.add(itm);
            }
        }

        if (cartItems.isEmpty()) {
            Toast.makeText(this, "Please select items to create bill.", Toast.LENGTH_SHORT).show();
            return;
        }

        btnPosCheckout.setEnabled(false);
        btnPosCheckout.setText("Processing Bill...");

        Map<String, Object> payload = new HashMap<>();
        payload.put("order_type", "WALK_IN");
        payload.put("customer_name", etCustomerName.getText().toString().trim());
        payload.put("payment_mode", paymentMode);
        payload.put("discount", walkInDiscount);
        payload.put("items", cartItems);

        if ("CASH".equals(paymentMode) && !etReceivedAmount.getText().toString().trim().isEmpty()) {
            try {
                payload.put("received_amount", Double.parseDouble(etReceivedAmount.getText().toString().trim()));
            } catch (Exception ignored) {}
        }

        ApiClient.getService().posCheckout(payload).enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
            @Override
            public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                btnPosCheckout.setEnabled(true);
                btnPosCheckout.setText(R.string.generate_and_print);

                if (response.isSuccessful() && response.body() != null && response.body().isSuccess()) {
                    Toast.makeText(PosCounterActivity.this, "Bill Generated and Sent to Printer Successfully!", Toast.LENGTH_LONG).show();
                    resetWalkInForm();
                    loadRecentBills();
                } else {
                    String err = "Checkout failed";
                    if (response.body() != null && response.body().getError() != null) {
                        err = response.body().getError();
                    }
                    Toast.makeText(PosCounterActivity.this, err, Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {
                btnPosCheckout.setEnabled(true);
                btnPosCheckout.setText(R.string.generate_and_print);
                Toast.makeText(PosCounterActivity.this, "Error: " + t.getMessage(), Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void resetWalkInForm() {
        for (MenuItemModel item : walkInDishes) {
            item.setSelectedQuantity(0);
        }
        walkInMenuAdapter.notifyDataSetChanged();
        etCustomerName.setText("");
        etDiscount.setText("");
        etReceivedAmount.setText("");
        recalculateWalkIn();
    }

    private void reprintBill(Long billId) {
        ApiClient.getService().reprintBill(billId).enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
            @Override
            public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                Toast.makeText(PosCounterActivity.this, "Reprint Dispatched!", Toast.LENGTH_SHORT).show();
            }
            @Override
            public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {
                Toast.makeText(PosCounterActivity.this, "Reprint error: " + t.getMessage(), Toast.LENGTH_SHORT).show();
            }
        });
    }
}
