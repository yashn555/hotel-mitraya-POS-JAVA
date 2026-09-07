package com.hotelmitraya.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

@Entity
@Table(name = "dining_tables")
public class DiningTable {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "table_number", unique = true, nullable = false)
    private Integer tableNumber;

    private Integer capacity = 4;

    @Column(length = 20)
    private String status = "VACANT"; // 'VACANT', 'OCCUPIED', 'RESERVED'

    @Column(name = "current_order_id")
    private Long currentOrderId;

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();

    public DiningTable() {}

    public DiningTable(Integer tableNumber, Integer capacity, String status) {
        this.tableNumber = tableNumber;
        this.capacity = capacity;
        this.status = status;
        this.updatedAt = LocalDateTime.now();
    }

    @PreUpdate
    public void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("id", this.id);
        map.put("table_number", this.tableNumber);
        map.put("capacity", this.capacity);
        map.put("status", this.status != null ? this.status : "VACANT");
        map.put("is_occupied", "OCCUPIED".equalsIgnoreCase(this.status));
        map.put("current_order_id", this.currentOrderId);
        map.put("updated_at", this.updatedAt != null ? 
                this.updatedAt.format(DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm a")) : null);
        return map;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Integer getTableNumber() { return tableNumber; }
    public void setTableNumber(Integer tableNumber) { this.tableNumber = tableNumber; }

    public Integer getCapacity() { return capacity; }
    public void setCapacity(Integer capacity) { this.capacity = capacity; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Long getCurrentOrderId() { return currentOrderId; }
    public void setCurrentOrderId(Long currentOrderId) { this.currentOrderId = currentOrderId; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
