package com.hotelmitraya.pos.ui.settings;

import android.os.Bundle;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;
import com.hotelmitraya.pos.HotelMitrayaApp;
import com.hotelmitraya.pos.R;
import com.hotelmitraya.pos.api.ApiClient;
import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;

import java.util.Map;

public class ServerSettingsActivity extends AppCompatActivity {

    private EditText etServerUrl;
    private TextView tvConnectionStatus;
    private Button btnTestServer, btnSaveServerConfig;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_server_settings);

        etServerUrl = findViewById(R.id.etServerUrl);
        tvConnectionStatus = findViewById(R.id.tvConnectionStatus);
        btnTestServer = findViewById(R.id.btnTestServer);
        btnSaveServerConfig = findViewById(R.id.btnSaveServerConfig);

        String currentUrl = HotelMitrayaApp.getInstance().getSessionManager().getServerUrl();
        etServerUrl.setText(currentUrl);

        btnTestServer.setOnClickListener(v -> testConnection());
        btnSaveServerConfig.setOnClickListener(v -> saveConfig());
    }

    private void testConnection() {
        String url = etServerUrl.getText().toString().trim();
        if (url.isEmpty()) {
            Toast.makeText(this, "Please enter a valid URL", Toast.LENGTH_SHORT).show();
            return;
        }

        HotelMitrayaApp.getInstance().getSessionManager().setServerUrl(url);
        tvConnectionStatus.setVisibility(View.VISIBLE);
        tvConnectionStatus.setText("Connecting to server...");
        tvConnectionStatus.setTextColor(getColor(R.color.primary_amber));

        ApiClient.getService().checkHealth().enqueue(new Callback<Map<String, Object>>() {
            @Override
            public void onResponse(Call<Map<String, Object>> call, Response<Map<String, Object>> response) {
                if (response.isSuccessful()) {
                    tvConnectionStatus.setText("✓ Connected successfully to Hotel Mitraya Server!");
                    tvConnectionStatus.setTextColor(getColor(R.color.status_vacant));
                } else {
                    tvConnectionStatus.setText("✗ Server replied with error code: " + response.code());
                    tvConnectionStatus.setTextColor(getColor(R.color.status_occupied));
                }
            }

            @Override
            public void onFailure(Call<Map<String, Object>> call, Throwable t) {
                tvConnectionStatus.setText("✗ Failed to connect: " + t.getMessage());
                tvConnectionStatus.setTextColor(getColor(R.color.status_occupied));
            }
        });
    }

    private void saveConfig() {
        String url = etServerUrl.getText().toString().trim();
        if (url.isEmpty()) {
            Toast.makeText(this, "Please enter a valid URL", Toast.LENGTH_SHORT).show();
            return;
        }
        HotelMitrayaApp.getInstance().getSessionManager().setServerUrl(url);
        Toast.makeText(this, "Server URL saved successfully!", Toast.LENGTH_SHORT).show();
        finish();
    }
}
