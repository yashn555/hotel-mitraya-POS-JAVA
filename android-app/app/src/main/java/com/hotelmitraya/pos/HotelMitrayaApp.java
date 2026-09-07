package com.hotelmitraya.pos;

import android.app.Application;
import com.hotelmitraya.pos.api.SessionManager;

public class HotelMitrayaApp extends Application {

    private static HotelMitrayaApp instance;
    private SessionManager sessionManager;

    @Override
    public void onCreate() {
        super.onCreate();
        instance = this;
        sessionManager = new SessionManager(this);
    }

    public static HotelMitrayaApp getInstance() {
        return instance;
    }

    public SessionManager getSessionManager() {
        return sessionManager;
    }
}
