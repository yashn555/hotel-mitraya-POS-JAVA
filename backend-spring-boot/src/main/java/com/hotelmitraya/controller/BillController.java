package com.hotelmitraya.controller;

import com.hotelmitraya.service.BillPdfService;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.io.File;
import java.nio.file.Files;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@RestController
@CrossOrigin(origins = "*")
public class BillController {

    private final BillPdfService billPdfService;

    public BillController(BillPdfService billPdfService) {
        this.billPdfService = billPdfService;
    }

    @GetMapping("/api/health")
    public ResponseEntity<Map<String, Object>> healthCheck() {
        Map<String, Object> response = new HashMap<>();
        response.put("status", "healthy");
        response.put("server_time", LocalDateTime.now().format(DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm:ss a")));
        response.put("bills_count", billPdfService.listBills(null).size());
        response.put("template_exists", true);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/next-bill-no")
    public ResponseEntity<Map<String, Object>> getNextBillNo() {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("next_bill_no", billPdfService.getNextSequentialBillNumber());
        return ResponseEntity.ok(response);
    }

    @PostMapping("/api/bills/generate")
    public ResponseEntity<Map<String, Object>> generateBill(@RequestBody Map<String, Object> data) {
        try {
            Map<String, Object> meta = billPdfService.generateBillPdf(data);
            String filePath = String.valueOf(meta.get("filepath"));
            File f = new File(filePath);
            if (f.exists()) {
                byte[] bytes = Files.readAllBytes(f.toPath());
                String b64 = Base64.getEncoder().encodeToString(bytes);
                meta.put("pdf_base64", b64);
                meta.put("pdf_data_url", "data:application/pdf;base64," + b64);
            }

            Map<String, Object> response = new HashMap<>();
            response.put("success", true);
            response.put("message", "Bill #" + data.get("bill_no") + " successfully generated as PDF!");
            response.put("bill", meta);
            return ResponseEntity.ok(response);
        } catch (Exception e) {
            Map<String, Object> err = new HashMap<>();
            err.put("success", false);
            err.put("error", e.getMessage());
            return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR).body(err);
        }
    }

    @GetMapping("/api/bills")
    public ResponseEntity<Map<String, Object>> listBills(@RequestParam(name = "q", required = false) String query) {
        List<Map<String, Object>> bills = billPdfService.listBills(query);
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("count", bills.size());
        response.put("bills", bills);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/bills/download/{filename:.+}")
    public ResponseEntity<Resource> downloadBill(@PathVariable String filename) {
        File folder = billPdfService.getBillsFolder();
        File file = new File(folder, filename);
        if (!file.exists()) {
            return ResponseEntity.notFound().build();
        }

        Resource resource = new FileSystemResource(file);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + file.getName() + "\"")
                .contentType(MediaType.APPLICATION_PDF)
                .body(resource);
    }

    @GetMapping("/api/bills/preview/{filename:.+}")
    public ResponseEntity<Resource> previewBill(@PathVariable String filename) {
        File folder = billPdfService.getBillsFolder();
        File file = new File(folder, filename);
        if (!file.exists()) {
            return ResponseEntity.notFound().build();
        }

        Resource resource = new FileSystemResource(file);
        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "inline; filename=\"" + file.getName() + "\"")
                .contentType(MediaType.APPLICATION_PDF)
                .body(resource);
    }

    @DeleteMapping("/api/bills/{filename:.+}")
    public ResponseEntity<Map<String, Object>> deleteBill(@PathVariable String filename) {
        boolean deleted = billPdfService.deleteBill(filename);
        Map<String, Object> response = new HashMap<>();
        if (deleted) {
            response.put("success", true);
            response.put("message", "Bill '" + filename + "' deleted successfully.");
            return ResponseEntity.ok(response);
        } else {
            response.put("success", false);
            response.put("error", "Bill not found");
            return ResponseEntity.status(404).body(response);
        }
    }
}
