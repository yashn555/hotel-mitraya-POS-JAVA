package com.hotelmitraya.pos.model;

import com.google.gson.annotations.SerializedName;
import java.util.List;

public class CategoryModel {

    @SerializedName("id")
    private Long id;

    @SerializedName("name")
    private String name;

    @SerializedName("display_order")
    private int displayOrder;

    @SerializedName("items")
    private List<MenuItemModel> items;

    public Long getId() { return id; }
    public String getName() { return name; }
    public int getDisplayOrder() { return displayOrder; }
    public List<MenuItemModel> getItems() { return items; }
}
