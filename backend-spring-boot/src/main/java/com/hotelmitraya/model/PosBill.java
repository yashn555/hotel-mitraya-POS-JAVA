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
@Table(name = "pos_bills")
public class PosBill {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "bill_number", length = 50, unique = true, nullable = false)
    private String billNumber; // POS-000001

    @Column(nullable = false)
    private Double subtotal = 0.0;

    @Column(nullable = false)
    private Double discount = 0.0;

    @Column(name = "total_amount", nullable = false)
    private Double totalAmount = 0.0;

    @Column(name = "payment_mode", length = 20, nullable = false)
    private String paymentMode = "CASH"; // CASH, UPI, CARD

    @Column(name = "received_amount")
    private Double receivedAmount;

    @Column(name = "change_amount")
    private Double changeAmount;

    @Column(name = "order_type", length = 20, nullable = false)
    private String orderType = "WALK_IN"; // 'WALK_IN' or 'DINING'

    @Column(name = "table_number")
    private Integer tableNumber; // Table 1 to 12

    @Column(name = "customer_name", length = 100)
    private String customerName;

    @Column(length = 255)
    private String notes;

    @Column(name = "cashier_role", length = 50)
    private String cashierRole = "cashier";

    @Column(length = 20)
    private String status = "COMPLETED"; // 'COMPLETED', 'OPEN', 'CANCELLED'

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();

    @OneToMany(mappedBy = "posBill", cascade = CascadeType.ALL, orphanRemoval = true, fetch = FetchType.LAZY)
    @JsonManagedReference
    private List<PosBillItem> items = new ArrayList<>();

    @OneToMany(mappedBy = "posBill", cascade = CascadeType.ALL, fetch = FetchType.LAZY)
    private List<PrintJob> printJobs = new ArrayList<>();

    public PosBill() {}

    @PreUpdate
    public void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    public String getTableLabel() {
        if (this.tableNumber != null && this.tableNumber > 0) {
            return "Table " + this.tableNumber;
        }
        return "Walk-in";
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("id", this.id);
        map.put("bill_number", this.billNumber);
        map.put("order_type", this.orderType != null ? this.orderType : "WALK_IN");
        map.put("table_number", this.tableNumber);
        map.put("table_label", getTableLabel());
        map.put("customer_name", this.customerName != null ? this.customerName : "");
        map.put("notes", this.notes != null ? this.notes : "");
        map.put("subtotal", this.subtotal != null ? this.subtotal : 0.0);
        map.put("discount", this.discount != null ? this.discount : 0.0);
        map.put("total_amount", this.totalAmount != null ? this.totalAmount : 0.0);
        map.put("payment_mode", this.paymentMode != null ? this.paymentMode : "CASH");
        map.put("received_amount", this.receivedAmount);
        map.put("change_amount", this.changeAmount);
        map.put("cashier_role", this.cashierRole);
        map.put("status", this.status);
        map.put("created_at", this.createdAt != null ? 
                this.createdAt.format(DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm a")) : null);
        map.put("updated_at", this.updatedAt != null ? 
                this.updatedAt.format(DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm a")) : null);
        map.put("date_iso", this.createdAt != null ? this.createdAt.toString() : null);
        map.put("items_count", this.items != null ? this.items.size() : 0);
        map.put("items", this.items != null ? 
                this.items.stream().map(PosBillItem::toMap).collect(Collectors.toList()) : new ArrayList<>());
        return map;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getBillNumber() { return billNumber; }
    public void setBillNumber(String billNumber) { this.billNumber = billNumber; }

    public Double getSubtotal() { return subtotal; }
    public void setSubtotal(Double subtotal) { this.subtotal = subtotal; }

    public Double getDiscount() { return discount; }
    public void setDiscount(Double discount) { this.discount = discount; }

    public Double getTotalAmount() { return totalAmount; }
    public void setTotalAmount(Double totalAmount) { this.totalAmount = totalAmount; }

    public String getPaymentMode() { return paymentMode; }
    public void setPaymentMode(String paymentMode) { this.paymentMode = paymentMode; }

    public Double getReceivedAmount() { return receivedAmount; }
    public void setReceivedAmount(Double receivedAmount) { this.receivedAmount = receivedAmount; }

    public Double getChangeAmount() { return changeAmount; }
    public void setChangeAmount(Double changeAmount) { this.changeAmount = changeAmount; }

    public String getOrderType() { return orderType; }
    public void setOrderType(String orderType) { this.orderType = orderType; }

    public Integer getTableNumber() { return tableNumber; }
    public void setTableNumber(Integer tableNumber) { this.tableNumber = tableNumber; }

    public String getCustomerName() { return customerName; }
    public void setCustomerName(String customerName) { this.customerName = customerName; }

    public String getNotes() { return notes; }
    public void setNotes(String notes) { this.notes = notes; }

    public String getCashierRole() { return cashierRole; }
    public void setCashierRole(String cashierRole) { this.cashierRole = cashierRole; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }

    public List<PosBillItem> getItems() { return items; }
    public void setItems(List<PosBillItem> items) { this.items = items; }

    public List<PrintJob> getPrintJobs() { return printJobs; }
    public void setPrintJobs(List<PrintJob> printJobs) { this.printJobs = printJobs; }
}
