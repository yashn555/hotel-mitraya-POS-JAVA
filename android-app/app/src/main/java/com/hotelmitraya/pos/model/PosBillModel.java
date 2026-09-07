package com.hotelmitraya.pos.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class PosBillModel {

    @SerializedName("id")
    private Long id;

    @SerializedName("bill_number")
    private String billNumber;

    @SerializedName("order_type")
    private String orderType;

    @SerializedName("table_number")
    private Integer tableNumber;

    @SerializedName("table_label")
    private String tableLabel;

    @SerializedName("customer_name")
    private String customerName;

    @SerializedName("subtotal")
    private double subtotal;

    @SerializedName("discount")
    private double discount;

    @SerializedName("total_amount")
    private double totalAmount;

    @SerializedName("payment_mode")
    private String paymentMode;

    @SerializedName("created_at")
    private String createdAt;

    @SerializedName("items")
    private List<OrderItemModel> items;

    public Long getId() { return id; }
    public String getBillNumber() { return billNumber; }
    public String getOrderType() { return orderType; }
    public Integer getTableNumber() { return tableNumber; }
    public String getTableLabel() { return tableLabel != null ? tableLabel : (tableNumber != null ? "Table " + tableNumber : "Walk-in"); }
    public String getCustomerName() { return customerName != null ? customerName : ""; }
    public double getSubtotal() { return subtotal; }
    public double getDiscount() { return discount; }
    public double getTotalAmount() { return totalAmount; }
    public String getPaymentMode() { return paymentMode; }
    public String getCreatedAt() { return createdAt; }
    public List<OrderItemModel> getItems() { return items; }
}
