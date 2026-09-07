package com.hotelmitraya.service;

import com.hotelmitraya.model.DiningTable;
import com.hotelmitraya.model.MenuItem;
import com.hotelmitraya.model.Order;
import com.hotelmitraya.model.OrderItem;
import com.hotelmitraya.repository.DiningTableRepository;
import com.hotelmitraya.repository.MenuItemRepository;
import com.hotelmitraya.repository.OrderRepository;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class OrderService {

    private final OrderRepository orderRepository;
    private final MenuItemRepository menuItemRepository;
    private final DiningTableRepository diningTableRepository;
    private final AuthService authService;

    public OrderService(
            OrderRepository orderRepository,
            MenuItemRepository menuItemRepository,
            DiningTableRepository diningTableRepository,
            AuthService authService) {
        this.orderRepository = orderRepository;
        this.menuItemRepository = menuItemRepository;
        this.diningTableRepository = diningTableRepository;
        this.authService = authService;
    }

    public synchronized String generateNextOrderNumber() {
        String todayPrefix = "ORD-" + LocalDate.now().format(DateTimeFormatter.ofPattern("yyyyMMdd")) + "-";
        Optional<Order> lastOrder = orderRepository.findFirstByOrderNumberStartingWithOrderByIdDesc(todayPrefix);
        if (lastOrder.isEmpty() || lastOrder.get().getOrderNumber() == null) {
            return todayPrefix + "001";
        }
        try {
            String lastNumStr = lastOrder.get().getOrderNumber().substring(todayPrefix.length());
            int nextNum = Integer.parseInt(lastNumStr) + 1;
            return String.format("%s%03d", todayPrefix, nextNum);
        } catch (Exception e) {
            long count = orderRepository.count();
            return String.format("%s%03d", todayPrefix, count + 1);
        }
    }

    public List<Map<String, Object>> getKitchenOrders() {
        List<Order> activeOrders = orderRepository.findByStatusInOrderByIdAsc(
                List.of("PLACED", "CONFIRMED", "PREPARING", "READY")
        );
        List<Map<String, Object>> result = new ArrayList<>();
        LocalDateTime now = LocalDateTime.now();

        for (Order o : activeOrders) {
            long elapsedMin = o.getCreatedAt() != null ? java.time.Duration.between(o.getCreatedAt(), now).toMinutes() : 0;
            Map<String, Object> ticket = new HashMap<>();
            ticket.put("id", o.getId());
            ticket.put("order_number", o.getOrderNumber());
            ticket.put("table_number", o.getTableNumber());
            ticket.put("table_label", o.getTableLabel());
            ticket.put("customer_name", o.getCustomerName() != null ? o.getCustomerName() : "");
            ticket.put("notes", o.getNotes() != null ? o.getNotes() : "");
            ticket.put("created_at_time", o.getCreatedAt() != null ? o.getCreatedAt().format(DateTimeFormatter.ofPattern("hh:mm a")) : "");
            ticket.put("elapsed_minutes", elapsedMin);

            List<Map<String, Object>> itemsList = new ArrayList<>();
            if (o.getItems() != null) {
                for (OrderItem itm : o.getItems()) {
                    Map<String, Object> itmMap = new HashMap<>();
                    itmMap.put("item_name", itm.getItemName());
                    itmMap.put("quantity", itm.getQuantity());
                    itmMap.put("notes", itm.getItemNotes() != null ? itm.getItemNotes() : "");
                    itemsList.add(itmMap);
                }
            }
            ticket.put("items", itemsList);
            result.add(ticket);
        }
        return result;
    }

    @Transactional
    public Map<String, Object> createOrder(Map<String, Object> data, Long userId, String role, String name, String ipAddress) {
        Map<String, Object> response = new HashMap<>();

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> cartItems = (List<Map<String, Object>>) data.get("items");
        if (cartItems == null || cartItems.isEmpty()) {
            response.put("success", false);
            response.put("error", "Cannot place empty order. Please select items.");
            return response;
        }

        String orderType = String.valueOf(data.getOrDefault("order_type", "DINING")).trim().toUpperCase();
        if (!List.of("DINING", "WALK_IN", "TAKEAWAY").contains(orderType)) {
            orderType = "DINING";
        }

        Integer tableNumber = null;
        if (data.get("table_number") != null) {
            try {
                int t = Integer.parseInt(String.valueOf(data.get("table_number")));
                if (t >= 1 && t <= 12) {
                    tableNumber = t;
                }
            } catch (Exception ignored) {}
        }

        String customerName = String.valueOf(data.getOrDefault("customer_name", "")).trim();
        String notes = String.valueOf(data.getOrDefault("notes", "")).trim();
        String source = String.valueOf(data.getOrDefault("source", role.toUpperCase())).trim().toUpperCase();

        // If active order exists on this table, append items to it
        if (tableNumber != null && "DINING".equals(orderType)) {
            Optional<Order> existingActive = orderRepository.findFirstByTableNumberAndOrderTypeAndStatusIn(
                    tableNumber, "DINING", List.of("PLACED", "CONFIRMED", "PREPARING", "READY")
            );
            if (existingActive.isPresent()) {
                return appendItemsToOrder(existingActive.get(), cartItems, notes, userId, role, name, ipAddress);
            }
        }

        String orderNumber = generateNextOrderNumber();
        double subtotal = 0.0;
        List<OrderItem> orderItemsList = new ArrayList<>();

        Order order = new Order();
        order.setOrderNumber(orderNumber);
        order.setSource(source);
        order.setOrderType(orderType);
        order.setTableNumber(tableNumber);
        order.setCustomerName(customerName);
        order.setNotes(notes);
        order.setStatus("PLACED");
        order.setCreatedByUserId(userId);
        order.setCreatedByRole(role);
        order.setCreatedByName(name != null ? name : "Staff");
        order.setCreatedAt(LocalDateTime.now());
        order.setUpdatedAt(LocalDateTime.now());

        for (Map<String, Object> entry : cartItems) {
            Long itemId = entry.get("menu_item_id") != null ? Long.valueOf(String.valueOf(entry.get("menu_item_id"))) :
                    (entry.get("id") != null ? Long.valueOf(String.valueOf(entry.get("id"))) : null);
            double qty = Double.parseDouble(String.valueOf(entry.getOrDefault("quantity", 1.0)));
            if (qty <= 0) continue;

            String itemNotes = entry.get("item_notes") != null ? String.valueOf(entry.get("item_notes")).trim() :
                    (entry.get("notes") != null ? String.valueOf(entry.get("notes")).trim() : null);
            String itemName = String.valueOf(entry.getOrDefault("name", entry.getOrDefault("item_name", ""))).trim();
            double unitPrice = Double.parseDouble(String.valueOf(entry.getOrDefault("unit_price", entry.getOrDefault("price", 0.0))));

            if (itemId != null) {
                Optional<MenuItem> mItem = menuItemRepository.findById(itemId);
                if (mItem.isPresent()) {
                    itemName = mItem.get().getName();
                    unitPrice = mItem.get().getPrice();
                }
            }

            double lineTotal = Math.round(qty * unitPrice * 100.0) / 100.0;
            subtotal += lineTotal;

            OrderItem orderItem = new OrderItem(order, itemId, itemName, unitPrice, qty, itemNotes, lineTotal);
            orderItemsList.add(orderItem);
        }

        if (orderItemsList.isEmpty()) {
            response.put("success", false);
            response.put("error", "No valid items to place order");
            return response;
        }

        subtotal = Math.round(subtotal * 100.0) / 100.0;
        order.setSubtotal(subtotal);
        order.setTotalAmount(subtotal);
        order.setItems(orderItemsList);

        orderRepository.save(order);

        if (tableNumber != null && "DINING".equals(orderType)) {
            diningTableRepository.findByTableNumber(tableNumber).ifPresent(tbl -> {
                tbl.setStatus("OCCUPIED");
                tbl.setCurrentOrderId(order.getId());
                diningTableRepository.save(tbl);
            });
        }

        authService.recordAuditLog("CREATE_ORDER", "ORDER", String.valueOf(order.getId()),
                "Created Order #" + order.getOrderNumber() + " (" + order.getTableLabel() + ", " + orderItemsList.size() + " items, Total: Rs." + subtotal + ")",
                userId, name, role, ipAddress);

        response.put("success", true);
        response.put("message", "Order #" + order.getOrderNumber() + " placed successfully!");
        response.put("order", order.toMap());
        return response;
    }

    private Map<String, Object> appendItemsToOrder(Order existingOrder, List<Map<String, Object>> newItems, String newNotes,
                                                   Long userId, String role, String name, String ipAddress) {
        Map<String, Object> response = new HashMap<>();
        double subtotal = existingOrder.getSubtotal() != null ? existingOrder.getSubtotal() : 0.0;
        int addedCount = 0;

        for (Map<String, Object> entry : newItems) {
            Long itemId = entry.get("menu_item_id") != null ? Long.valueOf(String.valueOf(entry.get("menu_item_id"))) :
                    (entry.get("id") != null ? Long.valueOf(String.valueOf(entry.get("id"))) : null);
            double qty = Double.parseDouble(String.valueOf(entry.getOrDefault("quantity", 1.0)));
            if (qty <= 0) continue;

            String itemNotes = entry.get("item_notes") != null ? String.valueOf(entry.get("item_notes")).trim() :
                    (entry.get("notes") != null ? String.valueOf(entry.get("notes")).trim() : null);
            String itemName = String.valueOf(entry.getOrDefault("name", entry.getOrDefault("item_name", ""))).trim();
            double unitPrice = Double.parseDouble(String.valueOf(entry.getOrDefault("unit_price", entry.getOrDefault("price", 0.0))));

            if (itemId != null) {
                Optional<MenuItem> mItem = menuItemRepository.findById(itemId);
                if (mItem.isPresent()) {
                    itemName = mItem.get().getName();
                    unitPrice = mItem.get().getPrice();
                }
            }

            double lineTotal = Math.round(qty * unitPrice * 100.0) / 100.0;
            subtotal += lineTotal;

            OrderItem matchedItem = null;
            for (OrderItem itm : existingOrder.getItems()) {
                if (Objects.equals(itm.getMenuItemId(), itemId) && itm.getItemName().equals(itemName) &&
                        Objects.equals(itm.getItemNotes(), itemNotes)) {
                    matchedItem = itm;
                    break;
                }
            }

            if (matchedItem != null) {
                matchedItem.setQuantity(matchedItem.getQuantity() + qty);
                matchedItem.setTotalPrice(Math.round(matchedItem.getQuantity() * matchedItem.getUnitPrice() * 100.0) / 100.0);
            } else {
                OrderItem dbItem = new OrderItem(existingOrder, itemId, itemName, unitPrice, qty, itemNotes, lineTotal);
                existingOrder.getItems().add(dbItem);
            }
            addedCount++;
        }

        if (newNotes != null && !newNotes.isEmpty()) {
            if (existingOrder.getNotes() != null && !existingOrder.getNotes().contains(newNotes)) {
                existingOrder.setNotes(existingOrder.getNotes() + "; " + newNotes);
            } else if (existingOrder.getNotes() == null) {
                existingOrder.setNotes(newNotes);
            }
        }

        existingOrder.setSubtotal(Math.round(subtotal * 100.0) / 100.0);
        existingOrder.setTotalAmount(Math.round(subtotal * 100.0) / 100.0);
        existingOrder.setUpdatedAt(LocalDateTime.now());
        orderRepository.save(existingOrder);

        authService.recordAuditLog("UPDATE_ORDER_ITEMS", "ORDER", String.valueOf(existingOrder.getId()),
                "Added " + addedCount + " items to Order #" + existingOrder.getOrderNumber() + " (New Total: Rs." + existingOrder.getTotalAmount() + ")",
                userId, name, role, ipAddress);

        response.put("success", true);
        response.put("message", "Added " + addedCount + " items to existing Order #" + existingOrder.getOrderNumber() + "!");
        response.put("order", existingOrder.toMap());
        return response;
    }

    @Transactional
    public Map<String, Object> updateOrder(Long orderId, Map<String, Object> data, Long userId, String role, String name, String ipAddress) {
        Map<String, Object> response = new HashMap<>();
        Optional<Order> orderOpt = orderRepository.findById(orderId);
        if (orderOpt.isEmpty()) {
            response.put("success", false);
            response.put("error", "Order not found");
            return response;
        }

        Order order = orderOpt.get();
        if (List.of("COMPLETED", "CANCELLED").contains(order.getStatus())) {
            response.put("success", false);
            response.put("error", "Cannot edit an order that is already " + order.getStatus());
            return response;
        }

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> cartItems = (List<Map<String, Object>>) data.get("items");

        if (cartItems == null || cartItems.isEmpty()) {
            order.setStatus("CANCELLED");
            order.setNotes((order.getNotes() != null ? order.getNotes() : "") + " [All items removed by waiter]");
            if (order.getTableNumber() != null) {
                diningTableRepository.findByTableNumber(order.getTableNumber()).ifPresent(tbl -> {
                    tbl.setStatus("VACANT");
                    tbl.setCurrentOrderId(null);
                    diningTableRepository.save(tbl);
                });
            }
            orderRepository.save(order);
            response.put("success", true);
            response.put("message", "All items removed. Order #" + order.getOrderNumber() + " cancelled and table freed.");
            response.put("order", order.toMap());
            return response;
        }

        order.getItems().clear();
        double subtotal = 0.0;
        List<OrderItem> newItems = new ArrayList<>();

        for (Map<String, Object> entry : cartItems) {
            Long itemId = entry.get("menu_item_id") != null ? Long.valueOf(String.valueOf(entry.get("menu_item_id"))) :
                    (entry.get("id") != null ? Long.valueOf(String.valueOf(entry.get("id"))) : null);
            double qty = Double.parseDouble(String.valueOf(entry.getOrDefault("quantity", 1.0)));
            if (qty <= 0) continue;

            String itemNotes = entry.get("item_notes") != null ? String.valueOf(entry.get("item_notes")).trim() :
                    (entry.get("notes") != null ? String.valueOf(entry.get("notes")).trim() : null);
            String itemName = String.valueOf(entry.getOrDefault("name", entry.getOrDefault("item_name", ""))).trim();
            double unitPrice = Double.parseDouble(String.valueOf(entry.getOrDefault("unit_price", entry.getOrDefault("price", 0.0))));

            if (itemId != null) {
                Optional<MenuItem> mItem = menuItemRepository.findById(itemId);
                if (mItem.isPresent()) {
                    itemName = mItem.get().getName();
                    unitPrice = mItem.get().getPrice();
                }
            }

            double lineTotal = Math.round(qty * unitPrice * 100.0) / 100.0;
            subtotal += lineTotal;

            OrderItem dbItem = new OrderItem(order, itemId, itemName, unitPrice, qty, itemNotes, lineTotal);
            newItems.add(dbItem);
        }

        if (newItems.isEmpty()) {
            response.put("success", false);
            response.put("error", "No valid items in update payload");
            return response;
        }

        subtotal = Math.round(subtotal * 100.0) / 100.0;
        order.getItems().addAll(newItems);
        order.setSubtotal(subtotal);
        order.setTotalAmount(subtotal);
        if (data.containsKey("notes")) {
            order.setNotes(String.valueOf(data.get("notes")).trim());
        }
        if (data.containsKey("customer_name")) {
            order.setCustomerName(String.valueOf(data.get("customer_name")).trim());
        }
        order.setUpdatedAt(LocalDateTime.now());
        orderRepository.save(order);

        authService.recordAuditLog("EDIT_ORDER", "ORDER", String.valueOf(order.getId()),
                "Waiter updated Order #" + order.getOrderNumber() + " (" + newItems.size() + " items, Total: Rs." + subtotal + ")",
                userId, name, role, ipAddress);

        response.put("success", true);
        response.put("message", "Order #" + order.getOrderNumber() + " updated successfully!");
        response.put("order", order.toMap());
        return response;
    }

    @Transactional
    public Map<String, Object> updateOrderStatus(Long orderId, String newStatus, Long userId, String role, String name, String ipAddress) {
        Map<String, Object> response = new HashMap<>();
        List<String> valid = List.of("PLACED", "CONFIRMED", "PREPARING", "READY", "COMPLETED", "CANCELLED");
        if (!valid.contains(newStatus)) {
            response.put("success", false);
            response.put("error", "Invalid status: " + newStatus);
            return response;
        }

        Optional<Order> orderOpt = orderRepository.findById(orderId);
        if (orderOpt.isEmpty()) {
            response.put("success", false);
            response.put("error", "Order not found");
            return response;
        }

        Order order = orderOpt.get();
        order.setStatus(newStatus);
        order.setUpdatedAt(LocalDateTime.now());

        if ("CANCELLED".equals(newStatus) && order.getTableNumber() != null) {
            diningTableRepository.findByTableNumber(order.getTableNumber()).ifPresent(tbl -> {
                if (Objects.equals(tbl.getCurrentOrderId(), order.getId())) {
                    tbl.setStatus("VACANT");
                    tbl.setCurrentOrderId(null);
                    diningTableRepository.save(tbl);
                }
            });
        }

        orderRepository.save(order);

        authService.recordAuditLog("STATUS_CHANGE", "ORDER", String.valueOf(order.getId()),
                "Order #" + order.getOrderNumber() + " status changed to " + newStatus,
                userId, name, role, ipAddress);

        response.put("success", true);
        response.put("message", "Order #" + order.getOrderNumber() + " is now " + newStatus);
        response.put("order", order.toMap());
        return response;
    }

    public List<Map<String, Object>> getOrders(String statusFilter, Integer tableNumber, boolean myOrdersOnly, Long userId) {
        List<String> statuses = null;
        if (statusFilter != null && !statusFilter.trim().isEmpty()) {
            statuses = Arrays.stream(statusFilter.split(",")).map(String::trim).collect(Collectors.toList());
        }
        Long filterUserId = myOrdersOnly ? userId : null;
        return orderRepository.findOrdersWithFilters(filterUserId, statuses, tableNumber)
                .stream().map(Order::toMap).collect(Collectors.toList());
    }

    public Optional<Map<String, Object>> getOrderById(Long orderId) {
        return orderRepository.findById(orderId).map(Order::toMap);
    }
}
