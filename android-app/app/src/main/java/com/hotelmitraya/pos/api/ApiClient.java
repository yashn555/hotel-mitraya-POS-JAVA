package com.hotelmitraya.pos.api;

import com.hotelmitraya.pos.HotelMitrayaApp;
import okhttp3.Cookie;
import okhttp3.CookieJar;
import okhttp3.HttpUrl;
import okhttp3.Interceptor;
import okhttp3.OkHttpClient;
import okhttp3.Request;
import okhttp3.Response;
import okhttp3.logging.HttpLoggingInterceptor;
import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;

public class ApiClient {

    private static Retrofit retrofit = null;
    private static String currentBaseUrl = "";
    private static final Map<String, List<Cookie>> cookieStore = new HashMap<>();

    public static void clearCookies() {
        cookieStore.clear();
    }

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

            CookieJar cookieJar = new CookieJar() {
                @Override
                public void saveFromResponse(HttpUrl url, List<Cookie> cookies) {
                    cookieStore.put(url.host(), cookies);
                }

                @Override
                public List<Cookie> loadForRequest(HttpUrl url) {
                    List<Cookie> cookies = cookieStore.get(url.host());
                    return cookies != null ? cookies : new ArrayList<>();
                }
            };

            Interceptor headerInterceptor = new Interceptor() {
                @Override
                public Response intercept(Chain chain) throws IOException {
                    SessionManager sm = HotelMitrayaApp.getInstance().getSessionManager();
                    Request.Builder builder = chain.request().newBuilder();
                    builder.addHeader("X-Requested-With", "XMLHttpRequest");
                    String role = sm.getUserRole();
                    if (role != null && !role.isEmpty()) {
                        builder.addHeader("X-User-Role", role);
                    }
                    if (sm.getUserId() > 0) {
                        builder.addHeader("X-User-Id", String.valueOf(sm.getUserId()));
                    }
                    return chain.proceed(builder.build());
                }
            };

            OkHttpClient client = new OkHttpClient.Builder()
                    .cookieJar(cookieJar)
                    .addInterceptor(headerInterceptor)
                    .addInterceptor(logging)
                    .connectTimeout(20, TimeUnit.SECONDS)
                    .readTimeout(25, TimeUnit.SECONDS)
                    .writeTimeout(25, TimeUnit.SECONDS)
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
