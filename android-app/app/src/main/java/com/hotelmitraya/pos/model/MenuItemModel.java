package com.hotelmitraya.pos.model;

import com.google.gson.annotations.SerializedName;

public class MenuItemModel {

    @SerializedName("id")
    private Long id;

    @SerializedName("category_id")
    private Long categoryId;

    @SerializedName("name")
    private String name;

    @SerializedName("price")
    private double price;

    @SerializedName("code")
    private String code;

    @SerializedName("is_available")
    private boolean isAvailable = true;

    @SerializedName("is_veg")
    private Boolean isVeg = true;

    // Local cart selection quantity and notes
    private int selectedQuantity = 0;
    private String itemNotes = "";

    public Long getId() { return id; }
    public Long getCategoryId() { return categoryId; }
    public String getName() { return name; }
    public double getPrice() { return price; }
    public String getCode() { return code != null ? code : ""; }
    public boolean isAvailable() { return isAvailable; }
    public boolean isVeg() { return isVeg == null || isVeg; }

    public int getSelectedQuantity() { return selectedQuantity; }
    public void setSelectedQuantity(int selectedQuantity) { this.selectedQuantity = Math.max(0, selectedQuantity); }

    public String getItemNotes() { return itemNotes != null ? itemNotes : ""; }
    public void setItemNotes(String itemNotes) { this.itemNotes = itemNotes; }
}
