package com.hotelmitraya.pos.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class DiningTableModel {

    @SerializedName("table_number")
    private int tableNumber;

    @SerializedName("status")
    private String status; // 'VACANT', 'OCCUPIED'

    @SerializedName("order_id")
    private Long orderId;

    @SerializedName("order_number")
    private String orderNumber;

    @SerializedName("customer_name")
    private String customerName;

    @SerializedName("notes")
    private String notes;

    @SerializedName("items_count")
    private int itemsCount;

    @SerializedName("total_amount")
    private double totalAmount;

    @SerializedName("elapsed_minutes")
    private long elapsedMinutes;

    @SerializedName("items")
    private List<OrderItemModel> items;

    public int getTableNumber() { return tableNumber; }
    public String getStatus() { return status != null ? status : "VACANT"; }
    public boolean isOccupied() { return "OCCUPIED".equalsIgnoreCase(status); }
    public Long getOrderId() { return orderId; }
    public String getOrderNumber() { return orderNumber; }
    public String getCustomerName() { return customerName; }
    public String getNotes() { return notes; }
    public int getItemsCount() { return itemsCount; }
    public double getTotalAmount() { return totalAmount; }
    public long getElapsedMinutes() { return elapsedMinutes; }
    public List<OrderItemModel> getItems() { return items; }
}
