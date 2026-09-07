package com.hotelmitraya.controller;

import com.hotelmitraya.model.PrintEvent;
import com.hotelmitraya.model.PrintJob;
import com.hotelmitraya.model.PrinterConfigModel;
import com.hotelmitraya.repository.OrderRepository;
import com.hotelmitraya.repository.PosBillRepository;
import com.hotelmitraya.repository.PrintEventRepository;
import com.hotelmitraya.repository.PrintJobRepository;
import com.hotelmitraya.repository.PrinterConfigRepository;
import com.hotelmitraya.service.AuthService;
import com.hotelmitraya.service.PrinterService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@CrossOrigin(origins = "*")
public class PrinterController {

    private final PrinterService printerService;
    private final PrinterConfigRepository printerConfigRepository;
    private final PrintJobRepository printJobRepository;
    private final PrintEventRepository printEventRepository;
    private final PosBillRepository posBillRepository;
    private final OrderRepository orderRepository;
    private final AuthService authService;

    public PrinterController(
            PrinterService printerService,
            PrinterConfigRepository printerConfigRepository,
            PrintJobRepository printJobRepository,
            PrintEventRepository printEventRepository,
            PosBillRepository posBillRepository,
            OrderRepository orderRepository,
            AuthService authService) {
        this.printerService = printerService;
        this.printerConfigRepository = printerConfigRepository;
        this.printJobRepository = printJobRepository;
        this.printEventRepository = printEventRepository;
        this.posBillRepository = posBillRepository;
        this.orderRepository = orderRepository;
        this.authService = authService;
    }

    @RequestMapping(value = "/api/printer/startup-init", method = {RequestMethod.GET, RequestMethod.POST})
    public ResponseEntity<Map<String, Object>> startupInit(HttpSession session) {
        List<Map<String, Object>> printers = printerService.listSystemPrinters();
        String detectedName = null;
        for (Map<String, Object> p : printers) {
            String name = String.valueOf(p.get("name")).toLowerCase();
            if (name.contains("pos") || name.contains("thermal") || name.contains("receipt") ||
                name.contains("58") || name.contains("80") || name.contains("epson") || name.contains("xp-") || name.contains("tvs")) {
                detectedName = String.valueOf(p.get("name"));
                break;
            }
        }
        if (detectedName == null && !printers.isEmpty()) {
            detectedName = String.valueOf(printers.get(0).get("name"));
        }

        PrinterConfigModel cfg = printerService.getActiveConfig();
        Map<String, Object> helloPayload = new HashMap<>();
        helloPayload.put("bill_number", "INIT-001");
        helloPayload.put("order_type", "STARTUP_CONFIRMATION");
        helloPayload.put("table_label", "Wired Printer Ready");
        helloPayload.put("cashier_role", session != null && session.getAttribute("user_name") != null ? session.getAttribute("user_name") : "System");
        helloPayload.put("payment_mode", "READY");
        helloPayload.put("subtotal", 0.0);
        helloPayload.put("discount", 0.0);
        helloPayload.put("total_amount", 0.0);
        helloPayload.put("items", List.of(
                Map.of("item_name", "HELLO - HOTEL MITRAYA", "quantity", 1, "unit_price", 0.0, "total_price", 0.0),
                Map.of("item_name", "Station: " + (detectedName != null ? detectedName : "Default"), "quantity", 1, "unit_price", 0.0, "total_price", 0.0),
                Map.of("item_name", "Status: ONLINE & READY", "quantity", 1, "unit_price", 0.0, "total_price", 0.0)
        ));

        Map<String, Object> customCfg = new HashMap<>(cfg.toMap());
        if (detectedName != null) {
            customCfg.put("printer_name", detectedName);
        }

        Map<String, Object> printJob = printerService.dispatchPrintJob(helloPayload, null, "STARTUP_HELLO", customCfg);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Printer '" + (detectedName != null ? detectedName : "Default") + "' identified and initialized with confirmation print!");
        response.put("identified_printer", detectedName != null ? detectedName : "Standard Spooler");
        response.put("total_printers_detected", printers.size());
        response.put("printers", printers);
        response.put("paper_width", cfg.getPaperWidth());
        response.put("print_job", printJob);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/printer/list")
    public ResponseEntity<Map<String, Object>> listPrinters() {
        List<Map<String, Object>> printers = printerService.listSystemPrinters();
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("count", printers.size());
        response.put("printers", printers);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/printer/status")
    public ResponseEntity<Map<String, Object>> printerStatus() {
        PrinterConfigModel cfg = printerService.getActiveConfig();
        long totalJobs = printJobRepository.count();
        long failedJobs = printJobRepository.countByStatus("FAILED");

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("connected", true);
        response.put("identified_printer", cfg.getPrinterName() != null && !cfg.getPrinterName().isEmpty() ? cfg.getPrinterName() : "Virtual ESC/POS");
        response.put("paper_width", cfg.getPaperWidth());
        response.put("columns", cfg.getPaperWidth() == 58 ? 32 : 48);
        response.put("config", cfg.toMap());
        response.put("stats", Map.of("total_jobs", totalJobs, "failed_jobs", failedJobs));
        return ResponseEntity.ok(response);
    }

    @PostMapping("/api/printer/config")
    public ResponseEntity<Map<String, Object>> updatePrinterConfig(
            @RequestBody Map<String, Object> data,
            HttpSession session,
            HttpServletRequest request) {

        PrinterConfigModel cfg = printerService.getActiveConfig();
        cfg.setName(String.valueOf(data.getOrDefault("name", "Counter Thermal Printer")).trim());
        String conn = String.valueOf(data.getOrDefault("connection_type", "WINDOWS_DRIVER")).trim().toUpperCase();
        cfg.setConnectionType(conn);
        int w = Integer.parseInt(String.valueOf(data.getOrDefault("paper_width", 80)));
        cfg.setPaperWidth(w == 58 ? 58 : 80);
        cfg.setPrinterName(String.valueOf(data.getOrDefault("printer_name", "")).trim());
        cfg.setIpAddress(String.valueOf(data.getOrDefault("ip_address", "")).trim());
        cfg.setPort(Integer.parseInt(String.valueOf(data.getOrDefault("port", 9100))));
        cfg.setCutEnabled(Boolean.parseBoolean(String.valueOf(data.getOrDefault("cut_enabled", true))));
        cfg.setHeaderTitle(String.valueOf(data.getOrDefault("header_title", "HOTEL MITRAYA")).trim());
        cfg.setFooterText(String.valueOf(data.getOrDefault("footer_text", "Thank You! Visit Again.")).trim());

        printerConfigRepository.save(cfg);

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String uName = session != null && session.getAttribute("username") != null ? String.valueOf(session.getAttribute("username")) : "Admin";
        String uRole = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "admin";
        String ip = request.getRemoteAddr();

        authService.recordAuditLog("PRINTER_CONFIG_UPDATE", "PRINTER", String.valueOf(cfg.getId()),
                "Updated printer configuration: " + conn + ", " + cfg.getPaperWidth() + "mm", userId, uName, uRole, ip);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Printer configuration updated successfully!");
        response.put("config", cfg.toMap());
        return ResponseEntity.ok(response);
    }

    @PostMapping("/api/printer/test")
    public ResponseEntity<Map<String, Object>> testPrint(
            @RequestBody(required = false) Map<String, Object> data,
            HttpSession session) {

        int paperWidth = data != null && data.get("paper_width") != null ?
                Integer.parseInt(String.valueOf(data.get("paper_width"))) : 80;

        Map<String, Object> testPayload = new HashMap<>();
        testPayload.put("bill_number", "TEST-001");
        testPayload.put("order_type", "TEST_PRINT");
        testPayload.put("table_label", "Test " + paperWidth + "mm Slip");
        testPayload.put("cashier_role", session != null && session.getAttribute("user_name") != null ? session.getAttribute("user_name") : "Staff");
        testPayload.put("payment_mode", "CASH");
        testPayload.put("subtotal", 440.0);
        testPayload.put("discount", 20.0);
        testPayload.put("total_amount", 420.0);
        testPayload.put("received_amount", 500.0);
        testPayload.put("change_amount", 80.0);
        testPayload.put("items", List.of(
                Map.of("item_name", "Special Dahi Dhapata", "quantity", 2, "unit_price", 110.0, "total_price", 220.0),
                Map.of("item_name", "Masala Chai", "quantity", 3, "unit_price", 20.0, "total_price", 60.0),
                Map.of("item_name", "Special Veg Thali", "quantity", 1, "unit_price", 160.0, "total_price", 160.0)
        ));

        Map<String, Object> customCfg = new HashMap<>();
        customCfg.put("paper_width", paperWidth);
        if (data != null && data.get("printer_name") != null) customCfg.put("printer_name", data.get("printer_name"));
        if (data != null && data.get("connection_type") != null) customCfg.put("connection_type", data.get("connection_type"));

        Map<String, Object> job = printerService.dispatchPrintJob(testPayload, null, "TEST_SLIP", customCfg);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Test print dispatched (" + paperWidth + "mm)!");
        response.put("job", job);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/api/printer/reprint/{billId}")
    public ResponseEntity<Map<String, Object>> reprintBill(@PathVariable Long billId) {
        Map<String, Object> result = printerService.reprintBill(billId);
        if (Boolean.FALSE.equals(result.get("success"))) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/api/printer/jobs")
    public ResponseEntity<Map<String, Object>> listPrintJobs(@RequestParam(defaultValue = "30") int limit) {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("jobs", printerService.getPrintJobs(limit));
        return ResponseEntity.ok(response);
    }

    @PostMapping("/api/printer/jobs/{jobId}/retry")
    public ResponseEntity<Map<String, Object>> retryJob(@PathVariable Long jobId) {
        Map<String, Object> result = printerService.retryJob(jobId);
        if (Boolean.FALSE.equals(result.get("success"))) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/api/display/live-orders")
    public ResponseEntity<Map<String, Object>> getLiveDisplayOrders(
            @RequestParam(name = "since_id", defaultValue = "0") Long sinceId,
            @RequestParam(defaultValue = "5") int limit) {

        Long maxId = printEventRepository.findMaxId();
        List<Map<String, Object>> newBills = new ArrayList<>();

        if (sinceId > 0) {
            List<PrintEvent> events = printEventRepository.findByIdGreaterThanOrderByIdAsc(sinceId);
            for (PrintEvent ev : events) {
                posBillRepository.findById(ev.getPosBillId()).ifPresent(b -> newBills.add(b.toMap()));
            }
        }

        List<Map<String, Object>> recentCompleted = posBillRepository.findByStatusOrderByIdDesc("COMPLETED")
                .stream().limit(limit).map(b -> b.toMap()).collect(Collectors.toList());

        long activeTablesCount = orderRepository.findByStatusInOrderByIdAsc(
                List.of("PLACED", "CONFIRMED", "PREPARING", "READY")
        ).size();

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("server_time", LocalDateTime.now().format(DateTimeFormatter.ofPattern("hh:mm:ss a")));
        response.put("bills", recentCompleted);
        response.put("new_bills", newBills);
        response.put("max_id", maxId);
        response.put("active_tables_count", activeTablesCount);
        return ResponseEntity.ok(response);
    }
}
