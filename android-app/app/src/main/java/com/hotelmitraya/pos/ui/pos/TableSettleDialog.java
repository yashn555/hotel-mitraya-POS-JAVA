package com.hotelmitraya.pos.ui.pos;

import android.app.Dialog;
import android.content.Context;
import android.os.Bundle;
import android.text.Editable;
import android.text.TextWatcher;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.*;
import androidx.annotation.NonNull;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;
import com.hotelmitraya.pos.R;
import com.hotelmitraya.pos.adapter.MenuItemAdapter;
import com.hotelmitraya.pos.api.ApiClient;
import com.hotelmitraya.pos.model.ApiResponse;
import com.hotelmitraya.pos.model.DiningTableModel;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.HashMap;
import java.util.Map;

public class TableSettleDialog extends Dialog {

    public interface OnSettleSuccessListener {
        void onSettled();
    }

    private final DiningTableModel table;
    private final OnSettleSuccessListener listener;

    private double subtotal;
    private double discount = 0.0;
    private double grandTotal;
    private String paymentMode = "CASH";

    private TextView tvSettleSubtotal, tvSettleGrandTotal, tvSettleChange;
    private EditText etSettleDiscount, etSettleReceived;
    private RadioButton rbSettleCash, rbSettleUpi, rbSettleCard;
    private LinearLayout layoutSettleCashFields;
    private Button btnConfirmSettlePrint;

    public TableSettleDialog(@NonNull Context context, DiningTableModel table, OnSettleSuccessListener listener) {
        super(context);
        this.table = table;
        this.listener = listener;
        this.subtotal = table.getTotalAmount();
        this.grandTotal = subtotal;
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        setContentView(R.layout.dialog_table_settle);

        if (getWindow() != null) {
            getWindow().setLayout(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        }

        initViews();
    }

    private void initViews() {
        TextView tvTitle = findViewById(R.id.tvSettleTableTitle);
        tvTitle.setText("Settle Table " + table.getTableNumber());

        TextView tvOrderNum = findViewById(R.id.tvSettleOrderNumber);
        tvOrderNum.setText(table.getOrderNumber() != null ? "Order #" + table.getOrderNumber() : "Active Tab");

        tvSettleSubtotal = findViewById(R.id.tvSettleSubtotal);
        tvSettleSubtotal.setText(String.format("₹%.2f", subtotal));

        tvSettleGrandTotal = findViewById(R.id.tvSettleGrandTotal);
        tvSettleGrandTotal.setText(String.format("₹%.2f", grandTotal));

        tvSettleChange = findViewById(R.id.tvSettleChange);
        etSettleDiscount = findViewById(R.id.etSettleDiscount);
        etSettleReceived = findViewById(R.id.etSettleReceived);
        layoutSettleCashFields = findViewById(R.id.layoutSettleCashFields);

        rbSettleCash = findViewById(R.id.rbSettleCash);
        rbSettleUpi = findViewById(R.id.rbSettleUpi);
        rbSettleCard = findViewById(R.id.rbSettleCard);

        RadioGroup rg = findViewById(R.id.rgSettlePayMode);
        rg.setOnCheckedChangeListener((group, checkedId) -> {
            if (checkedId == R.id.rbSettleCash) {
                paymentMode = "CASH";
                layoutSettleCashFields.setVisibility(View.VISIBLE);
            } else if (checkedId == R.id.rbSettleUpi) {
                paymentMode = "UPI";
                layoutSettleCashFields.setVisibility(View.GONE);
            } else {
                paymentMode = "CARD";
                layoutSettleCashFields.setVisibility(View.GONE);
            }
        });

        etSettleDiscount.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                try {
                    discount = Double.parseDouble(s.toString().trim());
                } catch (Exception e) {
                    discount = 0.0;
                }
                recalculate();
            }
            @Override
            public void afterTextChanged(Editable s) {}
        });

        etSettleReceived.addTextChangedListener(new TextWatcher() {
            @Override
            public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override
            public void onTextChanged(CharSequence s, int start, int before, int count) {
                recalculateChange();
            }
            @Override
            public void afterTextChanged(Editable s) {}
        });

        findViewById(R.id.btnCancelSettle).setOnClickListener(v -> dismiss());

        btnConfirmSettlePrint = findViewById(R.id.btnConfirmSettlePrint);
        btnConfirmSettlePrint.setOnClickListener(v -> performSettlement());
    }

    private void recalculate() {
        discount = Math.min(discount, subtotal);
        grandTotal = Math.max(0.0, subtotal - discount);
        tvSettleGrandTotal.setText(String.format("₹%.2f", grandTotal));
        recalculateChange();
    }

    private void recalculateChange() {
        try {
            double rec = Double.parseDouble(etSettleReceived.getText().toString().trim());
            double change = Math.max(0.0, rec - grandTotal);
            tvSettleChange.setText(String.format("Change: ₹%.2f", change));
        } catch (Exception e) {
            tvSettleChange.setText("Change: ₹0.00");
        }
    }

    private void performSettlement() {
        btnConfirmSettlePrint.setEnabled(false);
        btnConfirmSettlePrint.setText("Settling...");

        Map<String, Object> payload = new HashMap<>();
        payload.put("table_number", table.getTableNumber());
        if (table.getOrderId() != null) {
            payload.put("order_id", table.getOrderId());
        }
        payload.put("payment_mode", paymentMode);
        payload.put("discount", discount);

        if ("CASH".equals(paymentMode) && !etSettleReceived.getText().toString().trim().isEmpty()) {
            try {
                payload.put("received_amount", Double.parseDouble(etSettleReceived.getText().toString().trim()));
            } catch (Exception ignored) {}
        }

        ApiClient.getService().settleTable(payload).enqueue(new Callback<ApiResponse<Map<String, Object>>>() {
            @Override
            public void onResponse(Call<ApiResponse<Map<String, Object>>> call, Response<ApiResponse<Map<String, Object>>> response) {
                btnConfirmSettlePrint.setEnabled(true);
                btnConfirmSettlePrint.setText(R.string.settle_and_print);

                if (response.isSuccessful() && response.body() != null && response.body().isSuccess()) {
                    Toast.makeText(getContext(), "Table " + table.getTableNumber() + " settled and freed successfully!", Toast.LENGTH_SHORT).show();
                    dismiss();
                    if (listener != null) listener.onSettled();
                } else {
                    String err = "Failed to settle table";
                    if (response.body() != null && response.body().getError() != null) {
                        err = response.body().getError();
                    }
                    Toast.makeText(getContext(), err, Toast.LENGTH_SHORT).show();
                }
            }

            @Override
            public void onFailure(Call<ApiResponse<Map<String, Object>>> call, Throwable t) {
                btnConfirmSettlePrint.setEnabled(true);
                btnConfirmSettlePrint.setText(R.string.settle_and_print);
                Toast.makeText(getContext(), "Error: " + t.getMessage(), Toast.LENGTH_SHORT).show();
            }
        });
    }
}
