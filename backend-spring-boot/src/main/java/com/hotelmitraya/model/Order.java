package com.hotelmitraya.model;

import com.fasterxml.jackson.annotation.JsonManagedReference;
import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Entity
@Table(name = "orders")
public class Order {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "order_number", length = 50, unique = true, nullable = false)
    private String orderNumber;

    @Column(length = 20, nullable = false)
    private String source = "WAITER"; // 'WAITER', 'COUNTER', 'WALK_IN'

    @Column(name = "order_type", length = 20, nullable = false)
    private String orderType = "DINING"; // 'DINING', 'WALK_IN', 'TAKEAWAY'

    @Column(name = "table_number")
    private Integer tableNumber; // 1 to 12

    @Column(name = "customer_name", length = 100)
    private String customerName;

    @Column(length = 255)
    private String notes;

    @Column(length = 20, nullable = false)
    private String status = "PLACED"; // DRAFT, PLACED, CONFIRMED, PREPARING, READY, COMPLETED, CANCELLED

    @Column(nullable = false)
    private Double subtotal = 0.0;

    @Column(name = "total_amount", nullable = false)
    private Double totalAmount = 0.0;

    @Column(name = "created_by_user_id")
    private Long createdByUserId;

    @Column(name = "created_by_role", length = 30)
    private String createdByRole = "waiter";

    @Column(name = "created_by_name", length = 100)
    private String createdByName = "Staff";

    @Column(name = "bill_id")
    private Long billId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "bill_id", insertable = false, updatable = false)
    private PosBill bill;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();

    @OneToMany(mappedBy = "order", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    @JsonManagedReference
    private List<OrderItem> items = new ArrayList<>();

    public Order() {}

    @PreUpdate
    public void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    public String getTableLabel() {
        if (this.tableNumber != null && this.tableNumber > 0) {
            return "Table " + this.tableNumber;
        }
        return "Walk-in / Takeaway";
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("id", this.id);
        map.put("order_number", this.orderNumber);
        map.put("source", this.source);
        map.put("order_type", this.orderType);
        map.put("table_number", this.tableNumber);
        map.put("table_label", getTableLabel());
        map.put("customer_name", this.customerName != null ? this.customerName : "");
        map.put("notes", this.notes != null ? this.notes : "");
        map.put("status", this.status);
        map.put("subtotal", this.subtotal != null ? this.subtotal : 0.0);
        map.put("total_amount", this.totalAmount != null ? this.totalAmount : 0.0);
        map.put("created_by_user_id", this.createdByUserId);
        map.put("created_by_role", this.createdByRole);
        map.put("created_by_name", this.createdByName);
        map.put("bill_id", this.billId);
        map.put("bill_number", this.bill != null ? this.bill.getBillNumber() : null);
        map.put("created_at", this.createdAt != null ? 
                this.createdAt.format(DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm a")) : null);
        map.put("created_at_time", this.createdAt != null ? 
                this.createdAt.format(DateTimeFormatter.ofPattern("hh:mm a")) : null);
        map.put("updated_at", this.updatedAt != null ? 
                this.updatedAt.format(DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm a")) : null);
        map.put("date_iso", this.createdAt != null ? this.createdAt.toString() : null);
        map.put("items_count", this.items != null ? this.items.size() : 0);
        map.put("items", this.items != null ? 
                this.items.stream().map(OrderItem::toMap).collect(Collectors.toList()) : new ArrayList<>());
        return map;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getOrderNumber() { return orderNumber; }
    public void setOrderNumber(String orderNumber) { this.orderNumber = orderNumber; }

    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }

    public String getOrderType() { return orderType; }
    public void setOrderType(String orderType) { this.orderType = orderType; }

    public Integer getTableNumber() { return tableNumber; }
    public void setTableNumber(Integer tableNumber) { this.tableNumber = tableNumber; }

    public String getCustomerName() { return customerName; }
    public void setCustomerName(String customerName) { this.customerName = customerName; }

    public String getNotes() { return notes; }
    public void setNotes(String notes) { this.notes = notes; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Double getSubtotal() { return subtotal; }
    public void setSubtotal(Double subtotal) { this.subtotal = subtotal; }

    public Double getTotalAmount() { return totalAmount; }
    public void setTotalAmount(Double totalAmount) { this.totalAmount = totalAmount; }

    public Long getCreatedByUserId() { return createdByUserId; }
    public void setCreatedByUserId(Long createdByUserId) { this.createdByUserId = createdByUserId; }

    public String getCreatedByRole() { return createdByRole; }
    public void setCreatedByRole(String createdByRole) { this.createdByRole = createdByRole; }

    public String getCreatedByName() { return createdByName; }
    public void setCreatedByName(String createdByName) { this.createdByName = createdByName; }

    public Long getBillId() { return billId; }
    public void setBillId(Long billId) { this.billId = billId; }

    public PosBill getBill() { return bill; }
    public void setBill(PosBill bill) { this.bill = bill; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }

    public List<OrderItem> getItems() { return items; }
    public void setItems(List<OrderItem> items) { this.items = items; }
}
