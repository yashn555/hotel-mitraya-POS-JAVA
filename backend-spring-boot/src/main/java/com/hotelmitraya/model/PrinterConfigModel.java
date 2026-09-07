package com.hotelmitraya.model;

import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

@Entity
@Table(name = "printer_configs")
public class PrinterConfigModel {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(length = 100, nullable = false)
    private String name = "Counter Thermal Printer";

    @Column(name = "connection_type", length = 30)
    private String connectionType = "WINDOWS_DRIVER"; // 'WINDOWS_DRIVER', 'ESC_POS_RAW', 'NETWORK_RAW', 'BROWSER_PRINT'

    @Column(name = "paper_width")
    private Integer paperWidth = 80; // 58 or 80

    @Column(name = "printer_name", length = 150)
    private String printerName = "";

    @Column(name = "ip_address", length = 50)
    private String ipAddress = "";

    private Integer port = 9100;

    @Column(name = "is_default")
    private Boolean isDefault = true;

    @Column(name = "cut_enabled")
    private Boolean cutEnabled = true;

    @Column(name = "header_title", length = 100)
    private String headerTitle = "HOTEL MITRAYA";

    @Column(name = "footer_text", length = 255)
    private String footerText = "Thank You! Visit Again.";

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "updated_at")
    private LocalDateTime updatedAt = LocalDateTime.now();

    public PrinterConfigModel() {}

    @PreUpdate
    public void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("id", this.id);
        map.put("name", this.name);
        map.put("connection_type", this.connectionType);
        map.put("paper_width", this.paperWidth);
        map.put("printer_name", this.printerName != null ? this.printerName : "");
        map.put("ip_address", this.ipAddress != null ? this.ipAddress : "");
        map.put("port", this.port);
        map.put("is_default", this.isDefault);
        map.put("cut_enabled", this.cutEnabled);
        map.put("header_title", this.headerTitle);
        map.put("footer_text", this.footerText);
        return map;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getConnectionType() { return connectionType; }
    public void setConnectionType(String connectionType) { this.connectionType = connectionType; }

    public Integer getPaperWidth() { return paperWidth; }
    public void setPaperWidth(Integer paperWidth) { this.paperWidth = paperWidth; }

    public String getPrinterName() { return printerName; }
    public void setPrinterName(String printerName) { this.printerName = printerName; }

    public String getIpAddress() { return ipAddress; }
    public void setIpAddress(String ipAddress) { this.ipAddress = ipAddress; }

    public Integer getPort() { return port; }
    public void setPort(Integer port) { this.port = port; }

    public Boolean getIsDefault() { return isDefault; }
    public void setIsDefault(Boolean isDefault) { this.isDefault = isDefault; }

    public Boolean getCutEnabled() { return cutEnabled; }
    public void setCutEnabled(Boolean cutEnabled) { this.cutEnabled = cutEnabled; }

    public String getHeaderTitle() { return headerTitle; }
    public void setHeaderTitle(String headerTitle) { this.headerTitle = headerTitle; }

    public String getFooterText() { return footerText; }
    public void setFooterText(String footerText) { this.footerText = footerText; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getUpdatedAt() { return updatedAt; }
    public void setUpdatedAt(LocalDateTime updatedAt) { this.updatedAt = updatedAt; }
}
