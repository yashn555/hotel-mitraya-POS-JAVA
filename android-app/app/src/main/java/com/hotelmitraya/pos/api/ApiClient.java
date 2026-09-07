package com.hotelmitraya.pos.api;

import com.hotelmitraya.pos.HotelMitrayaApp;
import okhttp3.OkHttpClient;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

import java.util.concurrent.TimeUnit;

public class ApiClient {

    private static Retrofit retrofit = null;
    private static String currentBaseUrl = "";

    public static ApiService getService() {
        String baseUrl = HotelMitrayaApp.getInstance().getSessionManager().getServerUrl();
        if (baseUrl == null || (!baseUrl.startsWith("http://") && !baseUrl.startsWith("https://"))) {
            baseUrl = "https://hotel-mitraya-pos-java.onrender.com/";
        }
        if (!baseUrl.endsWith("/")) {
            baseUrl += "/";
        }

        if (retrofit == null || !baseUrl.equals(currentBaseUrl)) {
            currentBaseUrl = baseUrl;

            HttpLoggingInterceptor logging = new HttpLoggingInterceptor();
            logging.setLevel(HttpLoggingInterceptor.Level.BODY);

            OkHttpClient client = new OkHttpClient.Builder()
                    .connectTimeout(15, TimeUnit.SECONDS)
                    .readTimeout(20, TimeUnit.SECONDS)
                    .writeTimeout(20, TimeUnit.SECONDS)
                    .addInterceptor(logging)
                    .build();

            try {
                retrofit = new Retrofit.Builder()
                        .baseUrl(baseUrl)
                        .client(client)
                        .addConverterFactory(GsonConverterFactory.create())
                        .build();
            } catch (Exception e) {
                retrofit = new Retrofit.Builder()
                        .baseUrl("https://hotel-mitraya-pos-java.onrender.com/")
                        .client(client)
                        .addConverterFactory(GsonConverterFactory.create())
                        .build();
            }
        }

        return retrofit.create(ApiService.class);
    }
}
