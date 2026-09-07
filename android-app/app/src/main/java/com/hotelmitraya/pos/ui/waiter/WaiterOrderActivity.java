package com.hotelmitraya.pos.ui.waiter;

import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.hotelmitraya.pos.R;
import com.hotelmitraya.pos.adapter.CategoryTabAdapter;
import com.hotelmitraya.pos.adapter.MenuItemAdapter;
import com.hotelmitraya.pos.api.ApiClient;
import com.hotelmitraya.pos.model.ApiResponse;
import com.hotelmitraya.pos.model.CategoryModel;
import com.hotelmitraya.pos.model.MenuItemModel;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.*;

public class WaiterOrderActivity extends AppCompatActivity {

    private int tableNumber;
    private boolean isOccupied;
    private Long existingOrderId = null;
    private String existingOrderNumber = null;

    private Long currentCategoryId = null;
    private String currentSearchQuery = "";

    private CategoryTabAdapter categoryAdapter;
    private MenuItemAdapter menuAdapter;

    private TextView tvCartCount, tvCartSubtotal, tvOrderTableTitle, tvExistingOrderBadge;
    private EditText etCookingNotes;
    private Button btnSubmitOrder;

    private final List<MenuItemModel> allDishes = new ArrayList<>();

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_waiter_order);

        tableNumber = getIntent().getIntExtra("table_number", 1);
        isOccupied = getIntent().getBooleanExtra("is_occupied", false);
        if (getIntent().hasExtra("order_id")) {
            long oid = getIntent().getLongExtra("order_id", 0);
            if (oid > 0) {
                existingOrderId = oid;
            }
        }

        initViews();
        loadMenu();
    }

    private void initViews() {
        tvOrderTableTitle = findViewById(R.id.tvOrderTableTitle);
        tvExistingOrderBadge = findViewById(R.id.tvExistingOrderBadge);

        if (existingOrderId != null && existingOrderId > 0) {
            tvOrderTableTitle.setText("Edit Table " + tableNumber + " Order");
            tvExistingOrderBadge.setVisibility(View.VISIBLE);
            tvExistingOrderBadge.setText("EDITING ACTIVE ORDER");
        } else {
            tvOrderTableTitle.setText("New Order - Table " + tableNumber);
            tvExistingOrderBadge.setVisibility(View.GONE);
        }

        ImageButton btnBack = findViewById(R.id.btnBackToTables);
        btnBack.setOnClickListener(v -> finish());

        EditText etSearch = findViewById(R.id.etSearchDish);
        etSearch.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                currentSearchQuery = s.toString();
                menuAdapter.filter(currentCategoryId, currentSearchQuery);
            }
            @Override
            public void afterTextChanged(Editable s) {}
        });

        // Categories RecyclerView
        RecyclerView rvCategoryTabs = findViewById(R.id.rvCategoryTabs);
        rvCategoryTabs.setLayoutManager(new LinearLayoutManager(this, LinearLayoutManager.HORIZONTAL, false));
        categoryAdapter = new CategoryTabAdapter(this, categoryId -> {
            currentCategoryId = categoryId;
            menuAdapter.filter(currentCategoryId, currentSearchQuery);
        });
        rvCategoryTabs.setAdapter(categoryAdapter);

        // Menu Items RecyclerView
        RecyclerView rvMenuItems = findViewById(R.id.rvMenuItems);
        rvMenuItems.setLayoutManager(new LinearLayoutManager(this));
        menuAdapter = new MenuItemAdapter(this, (item, newQty) -> updateCartSummary());
        rvMenuItems.setAdapter(menuAdapter);

        // Bottom Cart Elements
        tvCartCount = findViewById(R.id.tvCartCount);
        tvCartSubtotal = findViewById(R.id.tvCartSubtotal);
        etCookingNotes = findViewById(R.id.etCookingNotes);
        btnSubmitOrder = findViewById(R.id.btnSubmitOrder);

        if (existingOrderId != null && existingOrderId > 0) {
            btnSubmitOrder.setText("💾 Update Order & Sync Kitchen");
        } else {
            btnSubmitOrder.setText(R.string.send_kot);
        }

        btnSubmitOrder.setOnClickListener(v -> submitOrder());
    }

    private void loadMenu() {
        ApiClient.getService().getWaiterMenu().enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
            @Override
            public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                if (response.isSuccessful() && response.body() != null && response.body().getCategories() != null) {
                    List<CategoryModel> categories = response.body().getCategories();
                    categoryAdapter.setCategories(categories);

                    allDishes.clear();
                    for (CategoryModel cat : categories) {
                        if (cat.getItems() != null) {
                            allDishes.addAll(cat.getItems());
                        }
                    }
                    menuAdapter.setItems(allDishes);

                    // If editing an existing active order, fetch and populate its items
                    if (existingOrderId != null && existingOrderId > 0) {
                        loadExistingOrderItems();
                    }
                }
            }

            @Override
            public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {
                Toast.makeText(WaiterOrderActivity.this, "Failed to load menu: " + t.getMessage(), Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void loadExistingOrderItems() {
        ApiClient.getService().getOrder(existingOrderId).enqueue(new Callback<Map<String, Object>>() {
            @Override
            public void onResponse(Call<Map<String, Object>> call, Response<Map<String, Object>> response) {
                if (response.isSuccessful() && response.body() != null && response.body().get("order") != null) {
                    @SuppressWarnings("unchecked")
                    Map<String, Object> orderMap = (Map<String, Object>) response.body().get("order");
                    existingOrderNumber = String.valueOf(orderMap.getOrDefault("order_number", ""));

                    if (orderMap.get("notes") != null) {
                        etCookingNotes.setText(String.valueOf(orderMap.get("notes")));
                    }

                    if (orderMap.get("items") != null) {
                        @SuppressWarnings("unchecked")
                        List<Map<String, Object>> orderItems = (List<Map<String, Object>>) orderMap.get("items");

                        for (Map<String, Object> itm : orderItems) {
                            String name = String.valueOf(itm.getOrDefault("item_name", ""));
                            int qty = ((Number) itm.getOrDefault("quantity", 1)).intValue();
                            Long menuItemId = itm.get("menu_item_id") != null ? ((Number) itm.get("menu_item_id")).longValue() : null;

                            for (MenuItemModel dish : allDishes) {
                                if ((menuItemId != null && menuItemId.equals(dish.getId())) || dish.getName().equalsIgnoreCase(name)) {
                                    dish.setSelectedQuantity(qty);
                                    if (itm.get("item_notes") != null) {
                                        dish.setItemNotes(String.valueOf(itm.get("item_notes")));
                                    }
                                    break;
                                }
                            }
                        }

                        menuAdapter.notifyDataSetChanged();
                        updateCartSummary();
                    }
                }
            }

            @Override
            public void onFailure(Call<Map<String, Object>> call, Throwable t) {
                // Non-fatal, waiter can still select items
            }
        });
    }

    private void updateCartSummary() {
        int totalQty = 0;
        double subtotal = 0.0;

        for (MenuItemModel item : allDishes) {
            if (item.getSelectedQuantity() > 0) {
                totalQty += item.getSelectedQuantity();
                subtotal += (item.getSelectedQuantity() * item.getPrice());
            }
        }

        tvCartCount.setText(totalQty + " items selected");
        tvCartSubtotal.setText(String.format("₹%.2f", subtotal));
    }

    private void submitOrder() {
        List<Map<String, Object>> cartItems = new ArrayList<>();
        for (MenuItemModel item : allDishes) {
            if (item.getSelectedQuantity() > 0) {
                Map<String, Object> itm = new HashMap<>();
                itm.put("menu_item_id", item.getId());
                itm.put("name", item.getName());
                itm.put("quantity", item.getSelectedQuantity());
                itm.put("unit_price", item.getPrice());
                if (!item.getItemNotes().isEmpty()) {
                    itm.put("item_notes", item.getItemNotes());
                }
                cartItems.add(itm);
            }
        }

        if (cartItems.isEmpty()) {
            Toast.makeText(this, "Please select at least 1 dish.", Toast.LENGTH_SHORT).show();
            return;
        }

        btnSubmitOrder.setEnabled(false);

        Map<String, Object> payload = new HashMap<>();
        payload.put("table_number", tableNumber);
        payload.put("order_type", "DINING");
        payload.put("notes", etCookingNotes.getText().toString().trim());
        payload.put("items", cartItems);

        if (existingOrderId != null && existingOrderId > 0) {
            // Update existing running order
            btnSubmitOrder.setText("Syncing Changes...");
            ApiClient.getService().updateOrder(existingOrderId, payload).enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
                @Override
                public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                    btnSubmitOrder.setEnabled(true);
                    btnSubmitOrder.setText("💾 Update Order & Sync Kitchen");

                    if (response.isSuccessful() && response.body() != null && response.body().isSuccess()) {
                        Toast.makeText(WaiterOrderActivity.this, "Order updated & sent to Kitchen & POS successfully!", Toast.LENGTH_LONG).show();
                        finish();
                    } else {
                        String err = "Failed to update order";
                        if (response.body() != null && response.body().getError() != null) {
                            err = response.body().getError();
                        }
                        Toast.makeText(WaiterOrderActivity.this, err, Toast.LENGTH_SHORT).show();
                    }
                }

                @Override
                public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {
                    btnSubmitOrder.setEnabled(true);
                    btnSubmitOrder.setText("💾 Update Order & Sync Kitchen");
                    Toast.makeText(WaiterOrderActivity.this, "Network error: " + t.getMessage(), Toast.LENGTH_SHORT).show();
                }
            });
        } else {
            // Place new KOT order
            btnSubmitOrder.setText("Sending KOT...");
            ApiClient.getService().createOrder(payload).enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
                @Override
                public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                    btnSubmitOrder.setEnabled(true);
                    btnSubmitOrder.setText(R.string.send_kot);

                    if (response.isSuccessful() && response.body() != null && response.body().isSuccess()) {
                        Toast.makeText(WaiterOrderActivity.this, "KOT Sent for Table " + tableNumber + " successfully!", Toast.LENGTH_LONG).show();
                        finish();
                    } else {
                        String err = "Failed to place order";
                        if (response.body() != null && response.body().getError() != null) {
                            err = response.body().getError();
                        }
                        Toast.makeText(WaiterOrderActivity.this, err, Toast.LENGTH_SHORT).show();
                    }
                }

                @Override
                public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {
                    btnSubmitOrder.setEnabled(true);
                    btnSubmitOrder.setText(R.string.send_kot);
                    Toast.makeText(WaiterOrderActivity.this, "Network error: " + t.getMessage(), Toast.LENGTH_SHORT).show();
                }
            });
        }
    }
}
