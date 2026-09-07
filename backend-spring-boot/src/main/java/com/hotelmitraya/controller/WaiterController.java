package com.hotelmitraya.controller;

import com.hotelmitraya.model.Category;
import com.hotelmitraya.model.MenuItem;
import com.hotelmitraya.model.Order;
import com.hotelmitraya.repository.CategoryRepository;
import com.hotelmitraya.repository.MenuItemRepository;
import com.hotelmitraya.repository.OrderRepository;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.CrossOrigin;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@CrossOrigin(origins = "*")
public class WaiterController {

    private final CategoryRepository categoryRepository;
    private final MenuItemRepository menuItemRepository;
    private final OrderRepository orderRepository;

    public WaiterController(
            CategoryRepository categoryRepository,
            MenuItemRepository menuItemRepository,
            OrderRepository orderRepository) {
        this.categoryRepository = categoryRepository;
        this.menuItemRepository = menuItemRepository;
        this.orderRepository = orderRepository;
    }

    @GetMapping("/api/waiter/menu")
    public ResponseEntity<Map<String, Object>> getWaiterMenu() {
        List<Category> categories = categoryRepository.findByIsActiveTrueOrderByDisplayOrderAscNameAsc();
        List<Map<String, Object>> catalog = new ArrayList<>();

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
            catalog.add(catMap);
        }

        List<MenuItem> uncategorized = menuItemRepository.findByCategoryIsNullAndIsAvailableTrueOrderByDisplayOrderAscNameAsc();
        if (!uncategorized.isEmpty()) {
            Map<String, Object> gen = new HashMap<>();
            gen.put("id", 0);
            gen.put("name", "General Dishes");
            gen.put("display_order", 999);
            gen.put("items", uncategorized.stream().map(MenuItem::toMap).collect(Collectors.toList()));
            catalog.add(gen);
        }

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("categories", catalog);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/waiter/tables")
    public ResponseEntity<Map<String, Object>> getWaiterTables() {
        List<Order> activeOrders = orderRepository.findByOrderTypeAndStatusIn(
                "DINING", List.of("PLACED", "CONFIRMED", "PREPARING", "READY")
        );
        Map<Integer, Order> orderMap = new HashMap<>();
        for (Order o : activeOrders) {
            if (o.getTableNumber() != null) {
                orderMap.put(o.getTableNumber(), o);
            }
        }

        List<Map<String, Object>> tables = new ArrayList<>();
        LocalDateTime now = LocalDateTime.now();

        for (int t = 1; t <= 12; t++) {
            Order ord = orderMap.get(t);
            Map<String, Object> tMap = new HashMap<>();
            tMap.put("table_number", t);
            if (ord != null) {
                long elapsed = ord.getCreatedAt() != null ? java.time.Duration.between(ord.getCreatedAt(), now).toMinutes() : 0;
                tMap.put("status", "OCCUPIED");
                tMap.put("order_id", ord.getId());
                tMap.put("order_number", ord.getOrderNumber());
                tMap.put("order_status", ord.getStatus());
                tMap.put("customer_name", ord.getCustomerName() != null ? ord.getCustomerName() : "");
                tMap.put("notes", ord.getNotes() != null ? ord.getNotes() : "");
                tMap.put("items_count", ord.getItems() != null ? ord.getItems().size() : 0);
                tMap.put("total_amount", ord.getTotalAmount() != null ? ord.getTotalAmount() : 0.0);
                tMap.put("created_by", ord.getCreatedByName());
                tMap.put("created_at_time", ord.getCreatedAt() != null ? ord.getCreatedAt().format(DateTimeFormatter.ofPattern("hh:mm a")) : "");
                tMap.put("elapsed_minutes", elapsed);
                tMap.put("items", ord.getItems() != null ? ord.getItems().stream().map(i -> i.toMap()).collect(Collectors.toList()) : new ArrayList<>());
            } else {
                tMap.put("status", "VACANT");
                tMap.put("order_id", null);
                tMap.put("order_number", null);
                tMap.put("order_status", "VACANT");
                tMap.put("customer_name", "");
                tMap.put("notes", "");
                tMap.put("items_count", 0);
                tMap.put("total_amount", 0.0);
                tMap.put("created_by", null);
                tMap.put("created_at_time", null);
                tMap.put("elapsed_minutes", 0);
                tMap.put("items", new ArrayList<>());
            }
            tables.add(tMap);
        }

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("tables", tables);
        return ResponseEntity.ok(response);
    }
}
