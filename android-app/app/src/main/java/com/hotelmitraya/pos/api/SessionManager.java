package com.hotelmitraya.pos.api;

import android.content.Context;
import android.content.SharedPreferences;

public class SessionManager {

    private static final String PREF_NAME = "hotel_mitraya_pos_pref";
    private static final String KEY_SERVER_URL = "server_url";
    private static final String KEY_IS_LOGGED_IN = "is_logged_in";
    private static final String KEY_USER_ROLE = "user_role";
    private static final String KEY_USER_NAME = "user_name";
    private static final String KEY_USER_ID = "user_id";
    private static final String KEY_PRINTER_WIDTH = "printer_width";

    private final SharedPreferences prefs;

    public SessionManager(Context context) {
        prefs = context.getSharedPreferences(PREF_NAME, Context.MODE_PRIVATE);
    }

    public String getServerUrl() {
        return prefs.getString(KEY_SERVER_URL, "https://hotel-mitraya-pos-java.onrender.com/");
    }

    public void setServerUrl(String url) {
        if (url == null) url = "";
        url = url.trim();
        if (!url.isEmpty() && !url.startsWith("http://") && !url.startsWith("https://")) {
            url = "http://" + url;
        }
        if (!url.isEmpty() && !url.endsWith("/")) {
            url += "/";
        }
        prefs.edit().putString(KEY_SERVER_URL, url).apply();
    }

    public boolean isLoggedIn() {
        return prefs.getBoolean(KEY_IS_LOGGED_IN, false);
    }

    public void setLogin(Long userId, String userName, String role) {
        prefs.edit()
                .putBoolean(KEY_IS_LOGGED_IN, true)
                .putLong(KEY_USER_ID, userId != null ? userId : 0)
                .putString(KEY_USER_NAME, userName)
                .putString(KEY_USER_ROLE, role)
                .apply();
    }

    public void logout() {
        prefs.edit()
                .putBoolean(KEY_IS_LOGGED_IN, false)
                .remove(KEY_USER_ID)
                .remove(KEY_USER_NAME)
                .remove(KEY_USER_ROLE)
                .apply();
    }

    public String getUserRole() {
        return prefs.getString(KEY_USER_ROLE, "waiter");
    }

    public String getUserName() {
        return prefs.getString(KEY_USER_NAME, "Staff");
    }

    public Long getUserId() {
        return prefs.getLong(KEY_USER_ID, 0);
    }

    public int getPrinterWidth() {
        return prefs.getInt(KEY_PRINTER_WIDTH, 80);
    }

    public void setPrinterWidth(int width) {
        prefs.edit().putInt(KEY_PRINTER_WIDTH, width).apply();
    }
}
