package com.hotelmitraya.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.hotelmitraya.model.AuditLog;
import com.hotelmitraya.model.Category;
import com.hotelmitraya.model.MenuItem;
import com.hotelmitraya.model.PosBill;
import com.hotelmitraya.repository.AuditLogRepository;
import com.hotelmitraya.repository.CategoryRepository;
import com.hotelmitraya.repository.MenuItemRepository;
import com.hotelmitraya.repository.PosBillRepository;
import com.hotelmitraya.service.AuthService;
import com.hotelmitraya.service.ReportService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@CrossOrigin(origins = "*")
public class AdminController {

    private final CategoryRepository categoryRepository;
    private final MenuItemRepository menuItemRepository;
    private final PosBillRepository posBillRepository;
    private final AuditLogRepository auditLogRepository;
    private final ReportService reportService;
    private final AuthService authService;
    private final ObjectMapper objectMapper;

    public AdminController(
            CategoryRepository categoryRepository,
            MenuItemRepository menuItemRepository,
            PosBillRepository posBillRepository,
            AuditLogRepository auditLogRepository,
            ReportService reportService,
            AuthService authService,
            ObjectMapper objectMapper) {
        this.categoryRepository = categoryRepository;
        this.menuItemRepository = menuItemRepository;
        this.posBillRepository = posBillRepository;
        this.auditLogRepository = auditLogRepository;
        this.reportService = reportService;
        this.authService = authService;
        this.objectMapper = objectMapper;
    }

    // =========================================================================
    // Category APIs
    // =========================================================================

    @GetMapping("/api/admin/categories")
    public ResponseEntity<Map<String, Object>> listCategories() {
        List<Map<String, Object>> categories = categoryRepository.findAllByOrderByDisplayOrderAscNameAsc()
                .stream().map(Category::toMap).collect(Collectors.toList());
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("categories", categories);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/api/admin/categories")
    public ResponseEntity<Map<String, Object>> saveCategory(
            @RequestBody Map<String, Object> data,
            HttpSession session,
            HttpServletRequest request) {

        Map<String, Object> response = new HashMap<>();
        Long id = data.get("id") != null ? Long.valueOf(String.valueOf(data.get("id"))) : null;
        String name = String.valueOf(data.getOrDefault("name", "")).trim();
        int order = Integer.parseInt(String.valueOf(data.getOrDefault("display_order", 0)));
        boolean active = Boolean.parseBoolean(String.valueOf(data.getOrDefault("is_active", true)));

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String uName = session != null && session.getAttribute("username") != null ? String.valueOf(session.getAttribute("username")) : "Admin";
        String uRole = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "admin";
        String ip = request.getRemoteAddr();

        if (name.isEmpty()) {
            response.put("success", false);
            response.put("error", "Category name is required");
            return ResponseEntity.badRequest().body(response);
        }

        if (id != null) {
            Optional<Category> catOpt = categoryRepository.findById(id);
            if (catOpt.isEmpty()) {
                response.put("success", false);
                response.put("error", "Category not found");
                return ResponseEntity.status(404).body(response);
            }
            Category category = catOpt.get();
            category.setName(name);
            category.setDisplayOrder(order);
            category.setIsActive(active);
            categoryRepository.save(category);

            authService.recordAuditLog("UPDATE_CATEGORY", "CATEGORY", String.valueOf(category.getId()),
                    "Updated category: " + name, userId, uName, uRole, ip);

            response.put("success", true);
            response.put("message", "Category '" + name + "' updated successfully!");
            response.put("category", category.toMap());
        } else {
            if (categoryRepository.findByNameIgnoreCase(name).isPresent()) {
                response.put("success", false);
                response.put("error", "Category '" + name + "' already exists");
                return ResponseEntity.badRequest().body(response);
            }

            Category category = new Category(name, order);
            category.setIsActive(active);
            categoryRepository.save(category);

            authService.recordAuditLog("CREATE_CATEGORY", "CATEGORY", String.valueOf(category.getId()),
                    "Created category: " + name, userId, uName, uRole, ip);

            response.put("success", true);
            response.put("message", "Category '" + name + "' created successfully!");
            response.put("category", category.toMap());
        }
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/api/admin/categories/{catId}")
    public ResponseEntity<Map<String, Object>> deleteCategory(
            @PathVariable Long catId,
            HttpSession session,
            HttpServletRequest request) {

        Map<String, Object> response = new HashMap<>();
        Optional<Category> catOpt = categoryRepository.findById(catId);
        if (catOpt.isEmpty()) {
            response.put("success", false);
            response.put("error", "Category not found");
            return ResponseEntity.status(404).body(response);
        }

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String uName = session != null && session.getAttribute("username") != null ? String.valueOf(session.getAttribute("username")) : "Admin";
        String uRole = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "admin";
        String ip = request.getRemoteAddr();

        String cName = catOpt.get().getName();
        categoryRepository.delete(catOpt.get());

        authService.recordAuditLog("DELETE_CATEGORY", "CATEGORY", String.valueOf(catId),
                "Deleted category: " + cName, userId, uName, uRole, ip);

        response.put("success", true);
        response.put("message", "Category deleted successfully!");
        return ResponseEntity.ok(response);
    }

    // =========================================================================
    // Menu Items APIs
    // =========================================================================

    @GetMapping("/api/admin/menu-items")
    public ResponseEntity<Map<String, Object>> listMenuItems(@RequestParam(name = "category_id", required = false) Long categoryId) {
        List<MenuItem> items;
        if (categoryId != null) {
            items = menuItemRepository.findByCategoryIdOrderByDisplayOrderAscNameAsc(categoryId);
        } else {
            items = menuItemRepository.findAllByOrderByDisplayOrderAscNameAsc();
        }

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("items", items.stream().map(MenuItem::toMap).collect(Collectors.toList()));
        return ResponseEntity.ok(response);
    }

    @PostMapping("/api/admin/menu-items")
    public ResponseEntity<Map<String, Object>> saveMenuItem(
            @RequestBody Map<String, Object> data,
            HttpSession session,
            HttpServletRequest request) {

        Map<String, Object> response = new HashMap<>();
        Long id = data.get("id") != null ? Long.valueOf(String.valueOf(data.get("id"))) : null;
        String name = String.valueOf(data.getOrDefault("name", "")).trim();
        double price = Double.parseDouble(String.valueOf(data.getOrDefault("price", 0.0)));
        Long categoryId = data.get("category_id") != null ? Long.valueOf(String.valueOf(data.get("category_id"))) : null;
        String code = data.get("code") != null ? String.valueOf(data.get("code")).trim() : null;
        boolean available = Boolean.parseBoolean(String.valueOf(data.getOrDefault("is_available", true)));
        int order = Integer.parseInt(String.valueOf(data.getOrDefault("display_order", 0)));

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String uName = session != null && session.getAttribute("username") != null ? String.valueOf(session.getAttribute("username")) : "Admin";
        String uRole = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "admin";
        String ip = request.getRemoteAddr();

        if (name.isEmpty()) {
            response.put("success", false);
            response.put("error", "Item name is required");
            return ResponseEntity.badRequest().body(response);
        }

        Category category = null;
        if (categoryId != null && categoryId > 0) {
            category = categoryRepository.findById(categoryId).orElse(null);
        }

        if (id != null) {
            Optional<MenuItem> itemOpt = menuItemRepository.findById(id);
            if (itemOpt.isEmpty()) {
                response.put("success", false);
                response.put("error", "Menu item not found");
                return ResponseEntity.status(404).body(response);
            }
            MenuItem item = itemOpt.get();
            double oldPrice = item.getPrice();
            item.setName(name);
            item.setPrice(price);
            item.setCategory(category);
            item.setCode(code);
            item.setIsAvailable(available);
            item.setDisplayOrder(order);
            menuItemRepository.save(item);

            String priceNote = oldPrice != price ? " (Price updated from Rs." + oldPrice + " to Rs." + price + ")" : "";
            authService.recordAuditLog("UPDATE_MENU_ITEM", "MENU_ITEM", String.valueOf(item.getId()),
                    "Updated item '" + name + "'" + priceNote, userId, uName, uRole, ip);

            response.put("success", true);
            response.put("message", "Item '" + name + "' updated successfully!");
            response.put("item", item.toMap());
        } else {
            MenuItem item = new MenuItem(category, name, price, code, order);
            item.setIsAvailable(available);
            menuItemRepository.save(item);

            authService.recordAuditLog("CREATE_MENU_ITEM", "MENU_ITEM", String.valueOf(item.getId()),
                    "Created menu item '" + name + "' (Rs." + price + ")", userId, uName, uRole, ip);

            response.put("success", true);
            response.put("message", "Item '" + name + "' added successfully!");
            response.put("item", item.toMap());
        }
        return ResponseEntity.ok(response);
    }

    @PostMapping("/api/admin/menu-items/{itemId}/toggle-availability")
    public ResponseEntity<Map<String, Object>> toggleItemAvailability(
            @PathVariable Long itemId,
            HttpSession session,
            HttpServletRequest request) {

        Map<String, Object> response = new HashMap<>();
        Optional<MenuItem> itemOpt = menuItemRepository.findById(itemId);
        if (itemOpt.isEmpty()) {
            response.put("success", false);
            response.put("error", "Menu item not found");
            return ResponseEntity.status(404).body(response);
        }

        MenuItem item = itemOpt.get();
        item.setIsAvailable(item.getIsAvailable() == null || !item.getIsAvailable());
        menuItemRepository.save(item);

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String uName = session != null && session.getAttribute("username") != null ? String.valueOf(session.getAttribute("username")) : "Admin";
        String uRole = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "admin";
        String ip = request.getRemoteAddr();

        String statusText = item.getIsAvailable() ? "Available" : "Disabled";
        authService.recordAuditLog("TOGGLE_ITEM_AVAILABILITY", "MENU_ITEM", String.valueOf(item.getId()),
                "Set '" + item.getName() + "' availability to " + statusText, userId, uName, uRole, ip);

        response.put("success", true);
        response.put("message", "Item '" + item.getName() + "' is now marked as " + statusText);
        response.put("is_available", item.getIsAvailable());
        return ResponseEntity.ok(response);
    }

    @DeleteMapping("/api/admin/menu-items/{itemId}")
    public ResponseEntity<Map<String, Object>> deleteMenuItem(
            @PathVariable Long itemId,
            HttpSession session,
            HttpServletRequest request) {

        Map<String, Object> response = new HashMap<>();
        Optional<MenuItem> itemOpt = menuItemRepository.findById(itemId);
        if (itemOpt.isEmpty()) {
            response.put("success", false);
            response.put("error", "Menu item not found");
            return ResponseEntity.status(404).body(response);
        }

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String uName = session != null && session.getAttribute("username") != null ? String.valueOf(session.getAttribute("username")) : "Admin";
        String uRole = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "admin";
        String ip = request.getRemoteAddr();

        String iName = itemOpt.get().getName();
        menuItemRepository.delete(itemOpt.get());

        authService.recordAuditLog("DELETE_MENU_ITEM", "MENU_ITEM", String.valueOf(itemId),
                "Deleted menu item '" + iName + "'", userId, uName, uRole, ip);

        response.put("success", true);
        response.put("message", "Item deleted successfully!");
        return ResponseEntity.ok(response);
    }

    // =========================================================================
    // Sales Reports & Analytics APIs
    // =========================================================================

    @GetMapping("/api/admin/reports/summary")
    public ResponseEntity<Map<String, Object>> getSalesSummary() {
        return ResponseEntity.ok(reportService.getSalesSummary());
    }

    @GetMapping("/api/admin/reports/best-sellers")
    public ResponseEntity<Map<String, Object>> getBestSellers(@RequestParam(defaultValue = "10") int limit) {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("best_sellers", reportService.getBestSellers(limit));
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/admin/pos-bills")
    public ResponseEntity<Map<String, Object>> listPosBills(
            @RequestParam(required = false) String q,
            @RequestParam(name = "payment_mode", required = false) String paymentMode,
            @RequestParam(required = false) String date,
            @RequestParam(defaultValue = "COMPLETED") String status) {

        LocalDateTime start = null;
        LocalDateTime end = null;
        if (date != null && !date.trim().isEmpty()) {
            try {
                LocalDate d = LocalDate.parse(date.trim());
                start = LocalDateTime.of(d, LocalTime.MIN);
                end = LocalDateTime.of(d, LocalTime.MAX);
            } catch (Exception ignored) {}
        }

        String safeStatus = "ALL".equalsIgnoreCase(status) ? null : status;
        String safePayMode = paymentMode != null && !paymentMode.trim().isEmpty() ? paymentMode.trim().toUpperCase() : null;
        String safeQ = q != null && !q.trim().isEmpty() ? q.trim() : null;

        List<Map<String, Object>> bills = posBillRepository.searchBills(safeStatus, safeQ, safePayMode, start, end)
                .stream().limit(100).map(PosBill::toMap).collect(Collectors.toList());

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("count", bills.size());
        response.put("bills", bills);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/admin/audit-logs")
    public ResponseEntity<Map<String, Object>> listAuditLogs(
            @RequestParam(required = false) String action,
            @RequestParam(required = false) String entity,
            @RequestParam(defaultValue = "100") int limit) {

        String safeAction = action != null && !action.trim().isEmpty() ? action.trim() : null;
        String safeEntity = entity != null && !entity.trim().isEmpty() ? entity.trim().toUpperCase() : null;

        List<Map<String, Object>> logs = auditLogRepository.searchAuditLogs(safeAction, safeEntity)
                .stream().limit(limit).map(AuditLog::toMap).collect(Collectors.toList());

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("count", logs.size());
        response.put("logs", logs);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/admin/database/backup")
    public ResponseEntity<byte[]> exportDatabaseBackup() throws Exception {
        Map<String, Object> backupData = reportService.exportDatabaseBackup();
        byte[] jsonBytes = objectMapper.writerWithDefaultPrettyPrinter().writeValueAsBytes(backupData);
        String timestamp = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd_HHmmss"));
        String filename = "mitraya_backup_" + timestamp + ".json";

        return ResponseEntity.ok()
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + filename + "\"")
                .contentType(MediaType.APPLICATION_JSON)
                .body(jsonBytes);
    }
}
