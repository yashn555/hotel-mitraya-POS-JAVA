package com.hotelmitraya.model;

import com.fasterxml.jackson.annotation.JsonBackReference;
import jakarta.persistence.*;
import java.util.HashMap;
import java.util.Map;

@Entity
@Table(name = "pos_bill_items")
public class PosBillItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "pos_bill_id", insertable = false, updatable = false)
    private Long posBillId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "pos_bill_id", nullable = false)
    @JsonBackReference
    private PosBill posBill;

    @Column(name = "menu_item_id")
    private Long menuItemId;

    @Column(name = "item_name", length = 150, nullable = false)
    private String itemName;

    @Column(name = "unit_price", nullable = false)
    private Double unitPrice = 0.0;

    @Column(nullable = false)
    private Double quantity = 1.0;

    @Column(name = "total_price", nullable = false)
    private Double totalPrice = 0.0;

    public PosBillItem() {}

    public PosBillItem(PosBill posBill, Long menuItemId, String itemName, Double unitPrice, Double quantity, Double totalPrice) {
        this.posBill = posBill;
        this.menuItemId = menuItemId;
        this.itemName = itemName;
        this.unitPrice = unitPrice;
        this.quantity = quantity;
        this.totalPrice = totalPrice;
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("id", this.id);
        map.put("pos_bill_id", this.posBill != null ? this.posBill.getId() : this.posBillId);
        map.put("menu_item_id", this.menuItemId);
        map.put("item_name", this.itemName);
        map.put("unit_price", this.unitPrice != null ? this.unitPrice : 0.0);
        map.put("quantity", this.quantity != null ? this.quantity : 1.0);
        map.put("total_price", this.totalPrice != null ? this.totalPrice : 0.0);
        return map;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getPosBillId() { return posBill != null ? posBill.getId() : posBillId; }
    public void setPosBillId(Long posBillId) { this.posBillId = posBillId; }

    public PosBill getPosBill() { return posBill; }
    public void setPosBill(PosBill posBill) { this.posBill = posBill; }

    public Long getMenuItemId() { return menuItemId; }
    public void setMenuItemId(Long menuItemId) { this.menuItemId = menuItemId; }

    public String getItemName() { return itemName; }
    public void setItemName(String itemName) { this.itemName = itemName; }

    public Double getUnitPrice() { return unitPrice; }
    public void setUnitPrice(Double unitPrice) { this.unitPrice = unitPrice; }

    public Double getQuantity() { return quantity; }
    public void setQuantity(Double quantity) { this.quantity = quantity; }

    public Double getTotalPrice() { return totalPrice; }
    public void setTotalPrice(Double totalPrice) { this.totalPrice = totalPrice; }
}
