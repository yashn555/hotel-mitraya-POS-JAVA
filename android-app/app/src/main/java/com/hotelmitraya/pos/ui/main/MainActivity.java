package com.hotelmitraya.pos.ui.main;

import android.content.Intent;
import android.os.Bundle;
import androidx.appcompat.app.AppCompatActivity;
import com.hotelmitraya.pos.HotelMitrayaApp;
import com.hotelmitraya.pos.ui.admin.AdminDashboardActivity;
import com.hotelmitraya.pos.ui.auth.LoginActivity;
import com.hotelmitraya.pos.ui.pos.PosCounterActivity;
import com.hotelmitraya.pos.ui.waiter.WaiterTablesActivity;

public class MainActivity extends AppCompatActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        if (!HotelMitrayaApp.getInstance().getSessionManager().isLoggedIn()) {
            startActivity(new Intent(this, LoginActivity.class));
            finish();
            return;
        }

        String role = HotelMitrayaApp.getInstance().getSessionManager().getUserRole();
        if ("waiter".equalsIgnoreCase(role)) {
            startActivity(new Intent(this, WaiterTablesActivity.class));
        } else if ("cashier".equalsIgnoreCase(role)) {
            startActivity(new Intent(this, PosCounterActivity.class));
        } else {
            startActivity(new Intent(this, AdminDashboardActivity.class));
        }
        finish();
    }
}
