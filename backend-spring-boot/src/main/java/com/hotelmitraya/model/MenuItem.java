package com.hotelmitraya.model;

import com.fasterxml.jackson.annotation.JsonBackReference;
import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Entity
@Table(name = "menu_items")
public class MenuItem {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "category_id", insertable = false, updatable = false)
    private Long categoryId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "category_id")
    @JsonBackReference
    private Category category;

    @Column(length = 150, nullable = false)
    private String name;

    @Column(nullable = false)
    private Double price = 0.0;

    @Column(name = "is_available")
    private Boolean isAvailable = true;

    @Column(name = "display_order")
    private Integer displayOrder = 0;

    @Column(length = 30)
    private String code;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    public MenuItem() {}

    public MenuItem(Category category, String name, Double price, String code, Integer displayOrder) {
        this.category = category;
        this.name = name;
        this.price = price;
        this.code = code;
        this.displayOrder = displayOrder;
        this.isAvailable = true;
        this.createdAt = LocalDateTime.now();
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("id", this.id);
        map.put("category_id", this.category != null ? this.category.getId() : this.categoryId);
        map.put("category_name", this.category != null ? this.category.getName() : "Uncategorized");
        map.put("name", this.name);
        map.put("price", this.price != null ? this.price : 0.0);
        map.put("is_available", this.isAvailable != null ? this.isAvailable : true);
        map.put("display_order", this.displayOrder != null ? this.displayOrder : 0);
        map.put("code", this.code != null ? this.code : "");
        return map;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getCategoryId() { return category != null ? category.getId() : categoryId; }
    public void setCategoryId(Long categoryId) { this.categoryId = categoryId; }

    public Category getCategory() { return category; }
    public void setCategory(Category category) { this.category = category; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public Double getPrice() { return price; }
    public void setPrice(Double price) { this.price = price; }

    public Boolean getIsAvailable() { return isAvailable; }
    public void setIsAvailable(Boolean isAvailable) { this.isAvailable = isAvailable; }

    public Integer getDisplayOrder() { return displayOrder; }
    public void setDisplayOrder(Integer displayOrder) { this.displayOrder = displayOrder; }

    public String getCode() { return code; }
    public void setCode(String code) { this.code = code; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
