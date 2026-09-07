package com.hotelmitraya.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

@Entity
@Table(name = "print_events")
public class PrintEvent {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "pos_bill_id", nullable = false)
    private Long posBillId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "pos_bill_id", insertable = false, updatable = false)
    private PosBill bill;

    @Column(name = "event_type", length = 30)
    private String eventType = "FINAL_BILL";

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    public PrintEvent() {}

    public PrintEvent(Long posBillId, String eventType) {
        this.posBillId = posBillId;
        this.eventType = eventType;
        this.createdAt = LocalDateTime.now();
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("event_id", this.id);
        map.put("event_type", this.eventType);
        map.put("created_at", this.createdAt != null ? 
                this.createdAt.format(DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm a")) : null);
        map.put("bill", this.bill != null ? this.bill.toMap() : null);
        return map;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getPosBillId() { return posBillId; }
    public void setPosBillId(Long posBillId) { this.posBillId = posBillId; }

    public PosBill getBill() { return bill; }
    public void setBill(PosBill bill) { this.bill = bill; }

    public String getEventType() { return eventType; }
    public void setEventType(String eventType) { this.eventType = eventType; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
