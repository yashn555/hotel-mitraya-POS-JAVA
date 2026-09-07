package com.hotelmitraya.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

@Entity
@Table(name = "audit_logs")
public class AuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id")
    private Long userId;

    @Column(length = 50)
    private String username = "System";

    @Column(length = 30)
    private String role = "system";

    @Column(length = 50, nullable = false)
    private String action; // LOGIN, CREATE_ORDER, SETTLE_BILL, REPRINT, UPDATE_PRICE, etc.

    @Column(length = 50)
    private String entity; // 'ORDER', 'BILL', 'MENU_ITEM', 'USER', 'PRINTER'

    @Column(name = "entity_id", length = 50)
    private String entityId;

    @Column(columnDefinition = "TEXT")
    private String details;

    @Column(name = "ip_address", length = 50)
    private String ipAddress;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    public AuditLog() {}

    public AuditLog(Long userId, String username, String role, String action, String entity, String entityId, String details, String ipAddress) {
        this.userId = userId;
        this.username = username != null ? username : "System";
        this.role = role != null ? role : "system";
        this.action = action;
        this.entity = entity;
        this.entityId = entityId;
        this.details = details;
        this.ipAddress = ipAddress;
        this.createdAt = LocalDateTime.now();
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("id", this.id);
        map.put("user_id", this.userId);
        map.put("username", this.username != null ? this.username : "System");
        map.put("role", this.role != null ? this.role : "staff");
        map.put("action", this.action);
        map.put("entity", this.entity != null ? this.entity : "");
        map.put("entity_id", this.entityId != null ? this.entityId : "");
        map.put("details", this.details != null ? this.details : "");
        map.put("ip_address", this.ipAddress != null ? this.ipAddress : "");
        map.put("created_at", this.createdAt != null ? 
                this.createdAt.format(DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm:ss a")) : null);
        map.put("date_iso", this.createdAt != null ? this.createdAt.toString() : null);
        return map;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }

    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }

    public String getRole() { return role; }
    public void setRole(String role) { this.role = role; }

    public String getAction() { return action; }
    public void setAction(String action) { this.action = action; }

    public String getEntity() { return entity; }
    public void setEntity(String entity) { this.entity = entity; }

    public String getEntityId() { return entityId; }
    public void setEntityId(String entityId) { this.entityId = entityId; }

    public String getDetails() { return details; }
    public void setDetails(String details) { this.details = details; }

    public String getIpAddress() { return ipAddress; }
    public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }
}
