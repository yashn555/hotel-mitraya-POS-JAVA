package com.hotelmitraya.pos.model;

import com.google.gson.annotations.SerializedName;

public class OrderItemModel {

    @SerializedName("id")
    private Long id;

    @SerializedName("menu_item_id")
    private Long menuItemId;

    @SerializedName("item_name")
    private String itemName;

    @SerializedName("unit_price")
    private double unitPrice;

    @SerializedName("quantity")
    private double quantity;

    @SerializedName("item_notes")
    private String itemNotes;

    @SerializedName("total_price")
    private double totalPrice;

    public Long getId() { return id; }
    public Long getMenuItemId() { return menuItemId; }
    public String getItemName() { return itemName; }
    public double getUnitPrice() { return unitPrice; }
    public double getQuantity() { return quantity; }
    public String getItemNotes() { return itemNotes != null ? itemNotes : ""; }
    public double getTotalPrice() { return totalPrice; }
}
