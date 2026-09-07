package com.hotelmitraya.model;

import com.fasterxml.jackson.annotation.JsonBackReference;
import jakarta.persistence.*;
import java.util.HashMap;
import java.util.Map;

@Entity
@Table(name = "order_items")
public class OrderItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_id", insertable = false, updatable = false)
    private Long orderId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "order_id", nullable = false)
    @JsonBackReference
    private Order order;

    @Column(name = "menu_item_id")
    private Long menuItemId;

    @Column(name = "item_name", length = 150, nullable = false)
    private String itemName;

    @Column(name = "unit_price", nullable = false)
    private Double unitPrice = 0.0;

    @Column(nullable = false)
    private Double quantity = 1.0;

    @Column(name = "item_notes", length = 255)
    private String itemNotes;

    @Column(name = "total_price", nullable = false)
    private Double totalPrice = 0.0;

    public OrderItem() {}

    public OrderItem(Order order, Long menuItemId, String itemName, Double unitPrice, Double quantity, String itemNotes, Double totalPrice) {
        this.order = order;
        this.menuItemId = menuItemId;
        this.itemName = itemName;
        this.unitPrice = unitPrice;
        this.quantity = quantity;
        this.itemNotes = itemNotes;
        this.totalPrice = totalPrice;
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("id", this.id);
        map.put("order_id", this.order != null ? this.order.getId() : this.orderId);
        map.put("menu_item_id", this.menuItemId);
        map.put("item_name", this.itemName);
        map.put("unit_price", this.unitPrice != null ? this.unitPrice : 0.0);
        map.put("quantity", this.quantity != null ? this.quantity : 1.0);
        map.put("item_notes", this.itemNotes != null ? this.itemNotes : "");
        map.put("total_price", this.totalPrice != null ? this.totalPrice : 0.0);
        return map;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getOrderId() { return order != null ? order.getId() : orderId; }
    public void setOrderId(Long orderId) { this.orderId = orderId; }

    public Order getOrder() { return order; }
    public void setOrder(Order order) { this.order = order; }

    public Long getMenuItemId() { return menuItemId; }
    public void setMenuItemId(Long menuItemId) { this.menuItemId = menuItemId; }

    public String getItemName() { return itemName; }
    public void setItemName(String itemName) { this.itemName = itemName; }

    public Double getUnitPrice() { return unitPrice; }
    public void setUnitPrice(Double unitPrice) { this.unitPrice = unitPrice; }

    public Double getQuantity() { return quantity; }
    public void setQuantity(Double quantity) { this.quantity = quantity; }

    public String getItemNotes() { return itemNotes; }
    public void setItemNotes(String itemNotes) { this.itemNotes = itemNotes; }

    public Double getTotalPrice() { return totalPrice; }
    public void setTotalPrice(Double totalPrice) { this.totalPrice = totalPrice; }
}
