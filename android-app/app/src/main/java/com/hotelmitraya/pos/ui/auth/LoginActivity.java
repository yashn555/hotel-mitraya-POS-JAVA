package com.hotelmitraya.pos.ui.auth;

import android.content.Intent;
import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.ImageButton;
import android.widget.ProgressBar;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.content.ContextCompat;
import com.hotelmitraya.pos.HotelMitrayaApp;
import com.hotelmitraya.pos.R;
import com.hotelmitraya.pos.api.ApiClient;
import com.hotelmitraya.pos.model.ApiResponse;
import com.hotelmitraya.pos.model.UserModel;
import com.hotelmitraya.pos.ui.admin.AdminDashboardActivity;
import com.hotelmitraya.pos.ui.pos.PosCounterActivity;
import com.hotelmitraya.pos.ui.settings.ServerSettingsActivity;
import com.hotelmitraya.pos.ui.waiter.WaiterTablesActivity;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.HashMap;
import java.util.Map;

public class LoginActivity extends AppCompatActivity {

    private String selectedRole = "admin";
    private StringBuilder enteredPin = new StringBuilder();

    private Button btnRoleAdmin, btnRoleCashier, btnRoleWaiter;
    private View dot1, dot2, dot3, dot4;
    private TextView tvErrorMessage;
    private Button btnUnlock;
    private ProgressBar progressBar;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Auto-login if session already active
        if (HotelMitrayaApp.getInstance().getSessionManager().isLoggedIn()) {
            String savedRole = HotelMitrayaApp.getInstance().getSessionManager().getUserRole();
            navigateByRole(savedRole);
            return;
        }

        setContentView(R.layout.activity_login);

        initViews();
        setupKeypad();
        setupRoles();
    }

    private void initViews() {
        btnRoleAdmin = findViewById(R.id.btnRoleAdmin);
        btnRoleCashier = findViewById(R.id.btnRoleCashier);
        btnRoleWaiter = findViewById(R.id.btnRoleWaiter);

        dot1 = findViewById(R.id.dot1);
        dot2 = findViewById(R.id.dot2);
        dot3 = findViewById(R.id.dot3);
        dot4 = findViewById(R.id.dot4);

        tvErrorMessage = findViewById(R.id.tvErrorMessage);
        btnUnlock = findViewById(R.id.btnUnlock);
        progressBar = findViewById(R.id.progressBar);

        ImageButton btnServerSettings = findViewById(R.id.btnServerSettings);
        btnServerSettings.setOnClickListener(v -> startActivity(new Intent(this, ServerSettingsActivity.class)));

        btnUnlock.setOnClickListener(v -> performLogin());
    }

    private void setupRoles() {
        btnRoleAdmin.setOnClickListener(v -> selectRole("admin"));
        btnRoleCashier.setOnClickListener(v -> selectRole("cashier"));
        btnRoleWaiter.setOnClickListener(v -> selectRole("waiter"));
    }

    private void selectRole(String role) {
        this.selectedRole = role;
        btnRoleAdmin.setBackgroundResource("admin".equals(role) ? R.drawable.bg_chip_role_selected : R.drawable.bg_chip_role_unselected);
        btnRoleAdmin.setTextColor(ContextCompat.getColor(this, "admin".equals(role) ? R.color.text_white : R.color.text_secondary));

        btnRoleCashier.setBackgroundResource("cashier".equals(role) ? R.drawable.bg_chip_role_selected : R.drawable.bg_chip_role_unselected);
        btnRoleCashier.setTextColor(ContextCompat.getColor(this, "cashier".equals(role) ? R.color.text_white : R.color.text_secondary));

        btnRoleWaiter.setBackgroundResource("waiter".equals(role) ? R.drawable.bg_chip_role_selected : R.drawable.bg_chip_role_unselected);
        btnRoleWaiter.setTextColor(ContextCompat.getColor(this, "waiter".equals(role) ? R.color.text_white : R.color.text_secondary));
    }

    private void setupKeypad() {
        int[] numIds = {R.id.btn0, R.id.btn1, R.id.btn2, R.id.btn3, R.id.btn4, R.id.btn5, R.id.btn6, R.id.btn7, R.id.btn8, R.id.btn9};
        for (int i = 0; i <= 9; i++) {
            final int digit = i;
            findViewById(numIds[i]).setOnClickListener(v -> appendDigit(String.valueOf(digit)));
        }

        findViewById(R.id.btnClear).setOnClickListener(v -> clearPin());
        findViewById(R.id.btnBackspace).setOnClickListener(v -> deleteDigit());
    }

    private void appendDigit(String d) {
        if (enteredPin.length() < 8) {
            enteredPin.append(d);
            updatePinDots();
        }
    }

    private void deleteDigit() {
        if (enteredPin.length() > 0) {
            enteredPin.deleteCharAt(enteredPin.length() - 1);
            updatePinDots();
        }
    }

    private void clearPin() {
        enteredPin.setLength(0);
        updatePinDots();
        tvErrorMessage.setVisibility(View.GONE);
    }

    private void updatePinDots() {
        int len = enteredPin.length();
        dot1.setBackgroundResource(len >= 1 ? R.drawable.bg_pin_dot_filled : R.drawable.bg_pin_dot_empty);
        dot2.setBackgroundResource(len >= 2 ? R.drawable.bg_pin_dot_filled : R.drawable.bg_pin_dot_empty);
        dot3.setBackgroundResource(len >= 3 ? R.drawable.bg_pin_dot_filled : R.drawable.bg_pin_dot_empty);
        dot4.setBackgroundResource(len >= 4 ? R.drawable.bg_pin_dot_filled : R.drawable.bg_pin_dot_empty);
    }

    private void performLogin() {
        String pin = enteredPin.toString().trim();
        if (pin.isEmpty()) {
            showError("Please enter your security PIN");
            return;
        }

        btnUnlock.setEnabled(false);
        btnUnlock.setText("");
        progressBar.setVisibility(View.VISIBLE);
        tvErrorMessage.setVisibility(View.GONE);

        Map<String, Object> body = new HashMap<>();
        body.put("pin", pin);
        body.put("role", selectedRole);

        ApiClient.getService().login(body).enqueue(new Callback<ApiResponse<UserModel>>() {
            @Override
            public void onResponse(Call<ApiResponse<UserModel>> call, Response<ApiResponse<UserModel>> response) {
                btnUnlock.setEnabled(true);
                btnUnlock.setText(R.string.unlock_access);
                progressBar.setVisibility(View.GONE);

                if (response.isSuccessful() && response.body() != null && response.body().isSuccess()) {
                    ApiResponse<UserModel> res = response.body();
                    String role = res.getRole() != null ? res.getRole() : selectedRole;
                    String name = res.getName() != null ? res.getName() : "Staff";
                    Long userId = res.getUserId();

                    HotelMitrayaApp.getInstance().getSessionManager().setLogin(userId, name, role);

                    Toast.makeText(LoginActivity.this, "Welcome " + name + "!", Toast.LENGTH_SHORT).show();
                    navigateByRole(role);
                } else {
                    String err = "Invalid PIN. Access denied.";
                    if (response.body() != null && response.body().getError() != null) {
                        err = response.body().getError();
                    }
                    showError(err);
                    clearPin();
                }
            }

            @Override
            public void onFailure(Call<ApiResponse<UserModel>> call, Throwable t) {
                btnUnlock.setEnabled(true);
                btnUnlock.setText(R.string.unlock_access);
                progressBar.setVisibility(View.GONE);
                showError("Server error: " + t.getMessage() + ". Check server URL in settings.");
            }
        });
    }

    private void showError(String msg) {
        tvErrorMessage.setText(msg);
        tvErrorMessage.setVisibility(View.VISIBLE);
    }

    private void navigateByRole(String role) {
        Intent intent;
        if ("waiter".equalsIgnoreCase(role)) {
            intent = new Intent(this, WaiterTablesActivity.class);
        } else if ("cashier".equalsIgnoreCase(role)) {
            intent = new Intent(this, PosCounterActivity.class);
        } else {
            intent = new Intent(this, AdminDashboardActivity.class);
        }
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TASK);
        startActivity(intent);
        finish();
    }
}
