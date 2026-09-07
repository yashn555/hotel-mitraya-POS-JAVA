package com.hotelmitraya.controller;

import com.hotelmitraya.service.OrderService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;

@RestController
@CrossOrigin(origins = "*")
public class OrderController {

    private final OrderService orderService;

    public OrderController(OrderService orderService) {
        this.orderService = orderService;
    }

    @GetMapping("/api/orders/kitchen")
    public ResponseEntity<Map<String, Object>> getKitchenOrders() {
        List<Map<String, Object>> tickets = orderService.getKitchenOrders();
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("server_time", LocalDateTime.now().format(DateTimeFormatter.ofPattern("hh:mm:ss a")));
        response.put("count", tickets.size());
        response.put("orders", tickets);
        return ResponseEntity.ok(response);
    }

    @PostMapping("/api/orders")
    public ResponseEntity<Map<String, Object>> createOrder(
            @RequestBody Map<String, Object> data,
            HttpSession session,
            HttpServletRequest request) {

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String role = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "waiter";
        String name = session != null && session.getAttribute("user_name") != null ? String.valueOf(session.getAttribute("user_name")) : "Staff";
        String ip = request.getRemoteAddr();

        Map<String, Object> result = orderService.createOrder(data, userId, role, name, ip);
        if (Boolean.FALSE.equals(result.get("success"))) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    @PutMapping("/api/orders/{orderId}")
    public ResponseEntity<Map<String, Object>> updateOrder(
            @PathVariable Long orderId,
            @RequestBody Map<String, Object> data,
            HttpSession session,
            HttpServletRequest request) {

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String role = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "waiter";
        String name = session != null && session.getAttribute("user_name") != null ? String.valueOf(session.getAttribute("user_name")) : "Staff";
        String ip = request.getRemoteAddr();

        Map<String, Object> result = orderService.updateOrder(orderId, data, userId, role, name, ip);
        if (Boolean.FALSE.equals(result.get("success"))) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/api/orders")
    public ResponseEntity<Map<String, Object>> listOrders(
            @RequestParam(required = false) String status,
            @RequestParam(name = "table_number", required = false) Integer tableNumber,
            @RequestParam(name = "my_orders", defaultValue = "false") boolean myOrders,
            HttpSession session) {

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        List<Map<String, Object>> orders = orderService.getOrders(status, tableNumber, myOrders, userId);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("count", orders.size());
        response.put("orders", orders);
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/orders/{orderId}")
    public ResponseEntity<Map<String, Object>> getOrder(@PathVariable Long orderId) {
        Optional<Map<String, Object>> orderOpt = orderService.getOrderById(orderId);
        if (orderOpt.isEmpty()) {
            Map<String, Object> err = new HashMap<>();
            err.put("success", false);
            err.put("error", "Order not found");
            return ResponseEntity.status(404).body(err);
        }
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("order", orderOpt.get());
        return ResponseEntity.ok(response);
    }

    @RequestMapping(value = "/api/orders/{orderId}/status", method = {RequestMethod.POST, RequestMethod.PATCH})
    public ResponseEntity<Map<String, Object>> updateStatus(
            @PathVariable Long orderId,
            @RequestBody Map<String, Object> data,
            HttpSession session,
            HttpServletRequest request) {

        String newStatus = String.valueOf(data.getOrDefault("status", "")).trim().toUpperCase();
        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String role = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "staff";
        String name = session != null && session.getAttribute("user_name") != null ? String.valueOf(session.getAttribute("user_name")) : "Staff";
        String ip = request.getRemoteAddr();

        Map<String, Object> result = orderService.updateOrderStatus(orderId, newStatus, userId, role, name, ip);
        if (Boolean.FALSE.equals(result.get("success"))) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    @PostMapping("/api/orders/{orderId}/cancel")
    public ResponseEntity<Map<String, Object>> cancelOrder(
            @PathVariable Long orderId,
            @RequestBody(required = false) Map<String, Object> data,
            HttpSession session,
            HttpServletRequest request) {

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String role = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "waiter";
        String name = session != null && session.getAttribute("user_name") != null ? String.valueOf(session.getAttribute("user_name")) : "Staff";
        String ip = request.getRemoteAddr();

        Map<String, Object> result = orderService.updateOrderStatus(orderId, "CANCELLED", userId, role, name, ip);
        if (Boolean.FALSE.equals(result.get("success"))) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }

    @GetMapping("/api/orders/live")
    public ResponseEntity<Map<String, Object>> getLiveOrders() {
        List<Map<String, Object>> activeOrders = orderService.getOrders("PLACED,CONFIRMED,PREPARING,READY", null, false, null);
        Map<Integer, Map<String, Object>> tableOrders = new HashMap<>();

        for (Map<String, Object> ord : activeOrders) {
            if (ord.get("table_number") != null) {
                try {
                    int tNum = Integer.parseInt(String.valueOf(ord.get("table_number")));
                    tableOrders.put(tNum, ord);
                } catch (Exception ignored) {}
            }
        }

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("server_time", LocalDateTime.now().format(DateTimeFormatter.ofPattern("hh:mm:ss a")));
        response.put("active_orders_count", activeOrders.size());
        response.put("active_orders", activeOrders);
        response.put("table_orders", tableOrders);
        return ResponseEntity.ok(response);
    }
}
