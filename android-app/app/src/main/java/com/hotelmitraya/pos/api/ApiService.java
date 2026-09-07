package com.hotelmitraya.pos.api;

import com.hotelmitraya.pos.model.*;
import retrofit2.Call;
import retrofit2.http.*;

import java.util.Map;

public interface ApiService {

    // Auth
    @POST("api/auth/login")
    Call<ApiResponse<UserModel>> login(@Body Map<String, Object> body);

    @GET("api/health")
    Call<Map<String, Object>> checkHealth();

    // Waiter
    @GET("api/waiter/tables")
    Call<ApiResponse<Map<String, Object>>> getWaiterTables();

    @GET("api/waiter/menu")
    Call<ApiResponse<Map<String, Object>>> getWaiterMenu();

    // Orders
    @POST("api/orders")
    Call<ApiResponse<Map<String, Object>>> createOrder(@Body Map<String, Object> orderPayload);

    @PUT("api/orders/{orderId}")
    Call<ApiResponse<Map<String, Object>>> updateOrder(@Path("orderId") Long orderId, @Body Map<String, Object> updatePayload);

    @GET("api/orders/{orderId}")
    Call<Map<String, Object>> getOrder(@Path("orderId") Long orderId);

    @GET("api/orders/kitchen")
    Call<Map<String, Object>> getKitchenOrders();

    @POST("api/orders/{orderId}/status")
    Call<ApiResponse<Map<String, Object>>> updateOrderStatus(@Path("orderId") Long orderId, @Body Map<String, Object> statusPayload);

    // POS & Tables
    @GET("api/pos/tables")
    Call<ApiResponse<Map<String, Object>>> getPosTables();

    @GET("api/pos/catalog")
    Call<ApiResponse<Map<String, Object>>> getPosCatalog();

    @POST("api/pos/checkout")
    Call<ApiResponse<Map<String, Object>>> posCheckout(@Body Map<String, Object> checkoutPayload);

    @POST("api/pos/tables/settle")
    Call<ApiResponse<Map<String, Object>>> settleTable(@Body Map<String, Object> settlePayload);

    @GET("api/pos/bills/recent")
    Call<ApiResponse<Map<String, Object>>> getRecentBills(@Query("limit") int limit);

    // Printer
    @POST("api/printer/reprint/{billId}")
    Call<ApiResponse<Map<String, Object>>> reprintBill(@Path("billId") Long billId);

    @POST("api/printer/test")
    Call<ApiResponse<Map<String, Object>>> testPrint(@Body Map<String, Object> payload);

    // Admin Reports
    @GET("api/admin/reports/summary")
    Call<ApiResponse<Map<String, Object>>> getSalesSummary();

    @GET("api/admin/reports/best-sellers")
    Call<ApiResponse<Map<String, Object>>> getBestSellers(@Query("limit") int limit);
}
