package com.hotelmitraya.controller;

import com.hotelmitraya.model.Category;
import com.hotelmitraya.model.MenuItem;
import com.hotelmitraya.repository.CategoryRepository;
import com.hotelmitraya.repository.MenuItemRepository;
import com.hotelmitraya.service.PosService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.*;
import java.util.stream.Collectors;

@RestController
@CrossOrigin(origins = "*")
public class PosController {

    private final PosService posService;
    private final CategoryRepository categoryRepository;
    private final MenuItemRepository menuItemRepository;

    public PosController(
            PosService posService,
            CategoryRepository categoryRepository,
            MenuItemRepository menuItemRepository) {
        this.posService = posService;
        this.categoryRepository = categoryRepository;
        this.menuItemRepository = menuItemRepository;
    }

    @GetMapping("/api/pos/catalog")
    public ResponseEntity<Map<String, Object>> getPosCatalog() {
        List<Category> categories = categoryRepository.findByIsActiveTrueOrderByDisplayOrderAscNameAsc();
        List<Map<String, Object>> result = new ArrayList<>();

        for (Category cat : categories) {
            Map<String, Object> catMap = new HashMap<>();
            catMap.put("id", cat.getId());
            catMap.put("name", cat.getName());
            catMap.put("display_order", cat.getDisplayOrder());

            List<Map<String, Object>> items = cat.getItems().stream()
                    .filter(i -> Boolean.TRUE.equals(i.getIsAvailable()))
                    .sorted(Comparator.comparing(MenuItem::getDisplayOrder).thenComparing(MenuItem::getName))
                    .map(MenuItem::toMap)
                    .collect(Collectors.toList());

            catMap.put("items", items);
            result.add(catMap);
        }

        List<MenuItem> uncategorized = menuItemRepository.findByCategoryIsNullAndIsAvailableTrueOrderByDisplayOrderAscNameAsc();
        if (!uncategorized.isEmpty()) {
            Map<String, Object> general = new HashMap<>();
            general.put("id", 0);
            general.put("name", "General Dishes");
            general.put("display_order", 999);
            general.put("items", uncategorized.stream().map(MenuItem::toMap).collect(Collectors.toList()));
            result.add(general);
        }

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("categories", result);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/pos/tables")
    public ResponseEntity<Map<String, Object>> getPosTables() {
        return ResponseEntity.ok(posService.getPosTables());
    }

    @GetMapping("/api/pos/tables/{tableNo}")
    public ResponseEntity<Map<String, Object>> getTableActiveOrder(@PathVariable int tableNo) {
        Map<String, Object> result = posService.getTableActiveOrder(tableNo);
        if (Boolean.FALSE.equals(result.get("success"))) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    @PostMapping("/api/pos/checkout")
    public ResponseEntity<Map<String, Object>> posCheckout(
            @RequestBody Map<String, Object> data,
            HttpSession session,
            HttpServletRequest request) {

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String role = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "cashier";
        String name = session != null && session.getAttribute("user_name") != null ? String.valueOf(session.getAttribute("user_name")) : "Staff";
        String ip = request.getRemoteAddr();

        Map<String, Object> result = posService.checkoutWalkIn(data, userId, role, name, ip);
        if (Boolean.FALSE.equals(result.get("success"))) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    @PostMapping("/api/pos/tables/settle")
    public ResponseEntity<Map<String, Object>> settleTable(
            @RequestBody Map<String, Object> data,
            HttpSession session,
            HttpServletRequest request) {

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String role = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "cashier";
        String name = session != null && session.getAttribute("user_name") != null ? String.valueOf(session.getAttribute("user_name")) : "Staff";
        String ip = request.getRemoteAddr();

        Map<String, Object> result = posService.settleTable(data, userId, role, name, ip);
        if (Boolean.FALSE.equals(result.get("success"))) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    @PostMapping("/api/pos/tables/{tableNo}/clear")
    public ResponseEntity<Map<String, Object>> clearTable(
            @PathVariable int tableNo,
            HttpSession session,
            HttpServletRequest request) {

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String role = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "cashier";
        String name = session != null && session.getAttribute("user_name") != null ? String.valueOf(session.getAttribute("user_name")) : "Staff";
        String ip = request.getRemoteAddr();

        Map<String, Object> result = posService.clearTable(tableNo, userId, role, name, ip);
        if (Boolean.FALSE.equals(result.get("success"))) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/api/pos/bills/recent")
    public ResponseEntity<Map<String, Object>> getRecentBills(@RequestParam(defaultValue = "25") int limit) {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("bills", posService.getRecentBills(limit));
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/pos/bills/{identifier}")
    public ResponseEntity<Map<String, Object>> getBillDetails(@PathVariable String identifier) {
        Optional<Map<String, Object>> billOpt = posService.getBillDetails(identifier);
        if (billOpt.isEmpty()) {
            Map<String, Object> err = new HashMap<>();
            err.put("success", false);
            err.put("error", "POS Bill not found");
            return ResponseEntity.status(404).body(err);
        }
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("bill", billOpt.get());
        return ResponseEntity.ok(response);
    }
}
