package com.hotelmitraya.model;

import com.fasterxml.jackson.annotation.JsonBackReference;
import jakarta.persistence.*;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.HashMap;
import java.util.Map;

@Entity
@Table(name = "print_jobs")
public class PrintJob {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "pos_bill_id")
    private Long posBillId;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "pos_bill_id", insertable = false, updatable = false)
    @JsonBackReference
    private PosBill posBill;

    @Column(name = "order_id")
    private Long orderId;

    @Column(name = "job_type", length = 30)
    private String jobType = "FINAL_BILL"; // 'FINAL_BILL', 'KOT', 'TEST_SLIP', 'STARTUP_HELLO'

    @Column(name = "printer_name", length = 100)
    private String printerName;

    @Column(name = "paper_width")
    private Integer paperWidth = 80; // 58 or 80

    @Column(length = 30)
    private String status = "PRINT_PENDING"; // 'PRINT_PENDING', 'PRINTING', 'PRINTED', 'FAILED'

    @Column(name = "error_message", columnDefinition = "TEXT")
    private String errorMessage;

    @Column(name = "retry_count")
    private Integer retryCount = 0;

    @Column(name = "created_at")
    private LocalDateTime createdAt = LocalDateTime.now();

    @Column(name = "printed_at")
    private LocalDateTime printedAt;

    public PrintJob() {}

    public Map<String, Object> toMap() {
        Map<String, Object> map = new HashMap<>();
        map.put("id", this.id);
        map.put("pos_bill_id", this.posBillId);
        map.put("order_id", this.orderId);
        map.put("job_type", this.jobType);
        map.put("printer_name", this.printerName != null ? this.printerName : "Default Thermal Printer");
        map.put("paper_width", this.paperWidth != null ? this.paperWidth : 80);
        map.put("status", this.status);
        map.put("error_message", this.errorMessage);
        map.put("retry_count", this.retryCount != null ? this.retryCount : 0);
        map.put("created_at", this.createdAt != null ? 
                this.createdAt.format(DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm:ss a")) : null);
        map.put("printed_at", this.printedAt != null ? 
                this.printedAt.format(DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm:ss a")) : null);
        map.put("bill_number", this.posBill != null ? this.posBill.getBillNumber() : null);
        return map;
    }

    // Getters and Setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public Long getPosBillId() { return posBillId; }
    public void setPosBillId(Long posBillId) { this.posBillId = posBillId; }

    public PosBill getPosBill() { return posBill; }
    public void setPosBill(PosBill posBill) { this.posBill = posBill; }

    public Long getOrderId() { return orderId; }
    public void setOrderId(Long orderId) { this.orderId = orderId; }

    public String getJobType() { return jobType; }
    public void setJobType(String jobType) { this.jobType = jobType; }

    public String getPrinterName() { return printerName; }
    public void setPrinterName(String printerName) { this.printerName = printerName; }

    public Integer getPaperWidth() { return paperWidth; }
    public void setPaperWidth(Integer paperWidth) { this.paperWidth = paperWidth; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public String getErrorMessage() { return errorMessage; }
    public void setErrorMessage(String errorMessage) { this.errorMessage = errorMessage; }

    public Integer getRetryCount() { return retryCount; }
    public void setRetryCount(Integer retryCount) { this.retryCount = retryCount; }

    public LocalDateTime getCreatedAt() { return createdAt; }
    public void setCreatedAt(LocalDateTime createdAt) { this.createdAt = createdAt; }

    public LocalDateTime getPrintedAt() { return printedAt; }
    public void setPrintedAt(LocalDateTime printedAt) { this.printedAt = printedAt; }
}
