package com.hotelmitraya.service;

import com.hotelmitraya.model.*;
import com.hotelmitraya.repository.*;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class PosService {

    private final PosBillRepository posBillRepository;
    private final PosBillItemRepository posBillItemRepository;
    private final OrderRepository orderRepository;
    private final DiningTableRepository diningTableRepository;
    private final MenuItemRepository menuItemRepository;
    private final PrintEventRepository printEventRepository;
    private final PrinterService printerService;
    private final AuthService authService;

    public PosService(
            PosBillRepository posBillRepository,
            PosBillItemRepository posBillItemRepository,
            OrderRepository orderRepository,
            DiningTableRepository diningTableRepository,
            MenuItemRepository menuItemRepository,
            PrintEventRepository printEventRepository,
            PrinterService printerService,
            AuthService authService) {
        this.posBillRepository = posBillRepository;
        this.posBillItemRepository = posBillItemRepository;
        this.orderRepository = orderRepository;
        this.diningTableRepository = diningTableRepository;
        this.menuItemRepository = menuItemRepository;
        this.printEventRepository = printEventRepository;
        this.printerService = printerService;
        this.authService = authService;
    }

    public synchronized String generateNextPosBillNumber() {
        Optional<PosBill> lastBill = posBillRepository.findFirstByOrderByIdDesc();
        if (lastBill.isEmpty() || lastBill.get().getBillNumber() == null) {
            return "POS-000001";
        }
        try {
            String rawNum = lastBill.get().getBillNumber().replace("POS-", "");
            int nextNum = Integer.parseInt(rawNum) + 1;
            return String.format("POS-%06d", nextNum);
        } catch (Exception e) {
            long count = posBillRepository.count();
            return String.format("POS-%06d", count + 1);
        }
    }

    public Map<String, Object> getPosTables() {
        List<Order> activeOrders = orderRepository.findByOrderTypeAndStatusIn(
                "DINING", List.of("PLACED", "CONFIRMED", "PREPARING", "READY")
        );
        Map<Integer, Order> orderByTable = new HashMap<>();
        for (Order o : activeOrders) {
            if (o.getTableNumber() != null) {
                orderByTable.put(o.getTableNumber(), o);
            }
        }

        List<Map<String, Object>> tablesList = new ArrayList<>();
        LocalDateTime now = LocalDateTime.now();

        for (int t = 1; t <= 12; t++) {
            Order activeO = orderByTable.get(t);
            if (activeO != null) {
                long elapsedMin = activeO.getCreatedAt() != null ? java.time.Duration.between(activeO.getCreatedAt(), now).toMinutes() : 0;
                Map<String, Object> orderDict = new HashMap<>(activeO.toMap());
                orderDict.put("elapsed_minutes", elapsedMin);

                Map<String, Object> tableEntry = new HashMap<>(orderDict);
                tableEntry.put("status", "OCCUPIED");
                tableEntry.put("active_order", orderDict);
                tableEntry.put("active_bill", orderDict);
                tablesList.add(tableEntry);
            } else {
                Map<String, Object> vacant = new HashMap<>();
                vacant.put("table_number", t);
                vacant.put("status", "VACANT");
                vacant.put("order_id", null);
                vacant.put("order_number", null);
                vacant.put("customer_name", "");
                vacant.put("notes", "");
                vacant.put("items_count", 0);
                vacant.put("subtotal", 0.0);
                vacant.put("total_amount", 0.0);
                vacant.put("created_by", null);
                vacant.put("created_at", null);
                vacant.put("elapsed_minutes", 0);
                vacant.put("order_status", "VACANT");
                vacant.put("items", new ArrayList<>());
                tablesList.add(vacant);
            }
        }

        Map<String, Object> result = new HashMap<>();
        result.put("success", true);
        result.put("total_tables", 12);
        result.put("occupied_count", orderByTable.size());
        result.put("vacant_count", 12 - orderByTable.size());
        result.put("tables", tablesList);
        return result;
    }

    public Map<String, Object> getTableActiveOrder(int tableNo) {
        Map<String, Object> response = new HashMap<>();
        if (tableNo < 1 || tableNo > 12) {
            response.put("success", false);
            response.put("error", "Table number must be between 1 and 12");
            return response;
        }

        Optional<Order> orderOpt = orderRepository.findFirstByTableNumberAndOrderTypeAndStatusIn(
                tableNo, "DINING", List.of("PLACED", "CONFIRMED", "PREPARING", "READY")
        );

        response.put("success", true);
        response.put("table_number", tableNo);

        if (orderOpt.isPresent()) {
            Map<String, Object> orderDict = orderOpt.get().toMap();
            orderDict.put("bill_number", orderOpt.get().getOrderNumber());
            orderDict.put("payment_mode", "CASH");
            orderDict.put("discount", 0.0);
            response.put("status", "OCCUPIED");
            response.put("order", orderDict);
            response.put("bill", orderDict);
        } else {
            response.put("status", "VACANT");
            response.put("order", null);
            response.put("bill", null);
        }
        return response;
    }

    @Transactional
    public Map<String, Object> checkoutWalkIn(Map<String, Object> data, Long userId, String role, String name, String ipAddress) {
        Map<String, Object> response = new HashMap<>();

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> cartItems = (List<Map<String, Object>>) data.get("items");
        if (cartItems == null || cartItems.isEmpty()) {
            response.put("success", false);
            response.put("error", "Cart is empty. Please add items to bill.");
            return response;
        }

        String orderType = String.valueOf(data.getOrDefault("order_type", "WALK_IN")).trim().toUpperCase();
        if (!List.of("WALK_IN", "DINING").contains(orderType)) {
            orderType = "WALK_IN";
        }

        Integer tableNumber = null;
        if (data.get("table_number") != null) {
            try {
                int t = Integer.parseInt(String.valueOf(data.get("table_number")));
                if (t >= 1 && t <= 12) tableNumber = t;
            } catch (Exception ignored) {}
        }

        String customerName = String.valueOf(data.getOrDefault("customer_name", "")).trim();
        String notes = String.valueOf(data.getOrDefault("notes", "")).trim();
        String paymentMode = String.valueOf(data.getOrDefault("payment_mode", "CASH")).trim().toUpperCase();
        if (!List.of("CASH", "UPI", "CARD").contains(paymentMode)) {
            paymentMode = "CASH";
        }

        double discount = Double.parseDouble(String.valueOf(data.getOrDefault("discount", 0.0)));
        Double receivedAmount = null;
        if (data.get("received_amount") != null && !String.valueOf(data.get("received_amount")).trim().isEmpty()) {
            receivedAmount = Double.parseDouble(String.valueOf(data.get("received_amount")));
        }

        String billNumber = generateNextPosBillNumber();
        double subtotal = 0.0;
        List<PosBillItem> dbBillItems = new ArrayList<>();

        PosBill bill = new PosBill();
        bill.setBillNumber(billNumber);
        bill.setOrderType(orderType);
        bill.setTableNumber(tableNumber);
        bill.setCustomerName(customerName);
        bill.setNotes(notes);
        bill.setPaymentMode(paymentMode);
        bill.setCashierRole(name != null ? name : role);
        bill.setStatus("COMPLETED");
        bill.setCreatedAt(LocalDateTime.now());
        bill.setUpdatedAt(LocalDateTime.now());

        for (Map<String, Object> entry : cartItems) {
            Long itemId = entry.get("menu_item_id") != null ? Long.valueOf(String.valueOf(entry.get("menu_item_id"))) :
                    (entry.get("id") != null ? Long.valueOf(String.valueOf(entry.get("id"))) : null);
            double qty = Double.parseDouble(String.valueOf(entry.getOrDefault("quantity", 1.0)));
            if (qty <= 0) continue;

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

            PosBillItem billItem = new PosBillItem(bill, itemId, itemName, unitPrice, qty, lineTotal);
            dbBillItems.add(billItem);
        }

        if (dbBillItems.isEmpty()) {
            response.put("success", false);
            response.put("error", "Invalid items in cart");
            return response;
        }

        subtotal = Math.round(subtotal * 100.0) / 100.0;
        discount = Math.min(discount, subtotal);
        double totalAmount = Math.max(0.0, Math.round((subtotal - discount) * 100.0) / 100.0);

        Double changeAmount = null;
        if ("CASH".equals(paymentMode)) {
            if (receivedAmount == null) receivedAmount = totalAmount;
            changeAmount = Math.max(0.0, Math.round((receivedAmount - totalAmount) * 100.0) / 100.0);
        }

        bill.setSubtotal(subtotal);
        bill.setDiscount(discount);
        bill.setTotalAmount(totalAmount);
        bill.setReceivedAmount(receivedAmount);
        bill.setChangeAmount(changeAmount);
        bill.setItems(dbBillItems);

        posBillRepository.save(bill);

        // Record print event for display station
        PrintEvent event = new PrintEvent(bill.getId(), "FINAL_BILL");
        printEventRepository.save(event);

        Map<String, Object> billData = bill.toMap();

        // Dispatch Thermal Print Job
        Map<String, Object> printRes = printerService.dispatchPrintJob(billData, bill.getId(), "FINAL_BILL");

        authService.recordAuditLog("POS_CHECKOUT", "BILL", String.valueOf(bill.getId()),
                "Walk-in Checkout: Bill #" + bill.getBillNumber() + ", Total: Rs." + totalAmount + " via " + paymentMode,
                userId, name, role, ipAddress);

        response.put("success", true);
        response.put("message", "Bill #" + bill.getBillNumber() + " generated successfully!");
        response.put("bill", billData);
        response.put("print_job", printRes);
        response.put("auto_print", true);
        return response;
    }

    @Transactional
    public Map<String, Object> settleTable(Map<String, Object> data, Long userId, String role, String name, String ipAddress) {
        Map<String, Object> response = new HashMap<>();

        int tableNo = 0;
        if (data.get("table_number") != null) {
            try {
                tableNo = Integer.parseInt(String.valueOf(data.get("table_number")));
            } catch (Exception ignored) {}
        }

        String paymentMode = String.valueOf(data.getOrDefault("payment_mode", "CASH")).trim().toUpperCase();
        if (!List.of("CASH", "UPI", "CARD").contains(paymentMode)) {
            paymentMode = "CASH";
        }

        double discount = Double.parseDouble(String.valueOf(data.getOrDefault("discount", 0.0)));
        Double receivedAmount = null;
        if (data.get("received_amount") != null && !String.valueOf(data.get("received_amount")).trim().isEmpty()) {
            receivedAmount = Double.parseDouble(String.valueOf(data.get("received_amount")));
        }

        Order order = null;
        if (tableNo > 0) {
            order = orderRepository.findFirstByTableNumberAndOrderTypeAndStatusIn(
                    tableNo, "DINING", List.of("PLACED", "CONFIRMED", "PREPARING", "READY")
            ).orElse(null);
        }
        if (order == null && data.get("order_id") != null) {
            order = orderRepository.findById(Long.valueOf(String.valueOf(data.get("order_id")))).orElse(null);
        }

        if (order == null) {
            response.put("success", false);
            response.put("error", "No active dining order found for Table " + tableNo);
            return response;
        }

        String billNumber = generateNextPosBillNumber();
        double subtotal = order.getSubtotal() != null ? order.getSubtotal() : 0.0;
        discount = Math.min(discount, subtotal);
        double totalAmount = Math.max(0.0, Math.round((subtotal - discount) * 100.0) / 100.0);

        Double changeAmount = null;
        if ("CASH".equals(paymentMode)) {
            if (receivedAmount == null) receivedAmount = totalAmount;
            changeAmount = Math.max(0.0, Math.round((receivedAmount - totalAmount) * 100.0) / 100.0);
        }

        PosBill bill = new PosBill();
        bill.setBillNumber(billNumber);
        bill.setOrderType("DINING");
        bill.setTableNumber(order.getTableNumber());
        bill.setCustomerName(order.getCustomerName());
        bill.setNotes(order.getNotes());
        bill.setSubtotal(subtotal);
        bill.setDiscount(discount);
        bill.setTotalAmount(totalAmount);
        bill.setPaymentMode(paymentMode);
        bill.setReceivedAmount(receivedAmount);
        bill.setChangeAmount(changeAmount);
        bill.setCashierRole(name != null ? name : role);
        bill.setStatus("COMPLETED");
        bill.setCreatedAt(LocalDateTime.now());
        bill.setUpdatedAt(LocalDateTime.now());

        List<PosBillItem> billItems = new ArrayList<>();
        if (order.getItems() != null) {
            for (OrderItem ordItem : order.getItems()) {
                billItems.add(new PosBillItem(
                        bill,
                        ordItem.getMenuItemId(),
                        ordItem.getItemName(),
                        ordItem.getUnitPrice(),
                        ordItem.getQuantity(),
                        ordItem.getTotalPrice()
                ));
            }
        }
        bill.setItems(billItems);

        posBillRepository.save(bill);

        // Mark order as completed
        order.setStatus("COMPLETED");
        order.setBillId(bill.getId());
        order.setUpdatedAt(LocalDateTime.now());
        orderRepository.save(order);

        // Free Table
        if (order.getTableNumber() != null) {
            diningTableRepository.findByTableNumber(order.getTableNumber()).ifPresent(tbl -> {
                tbl.setStatus("VACANT");
                tbl.setCurrentOrderId(null);
                diningTableRepository.save(tbl);
            });
        }

        // Record print event for display station
        PrintEvent event = new PrintEvent(bill.getId(), "FINAL_BILL");
        printEventRepository.save(event);

        Map<String, Object> billData = bill.toMap();

        // Dispatch Thermal Print Job
        Map<String, Object> printRes = printerService.dispatchPrintJob(billData, bill.getId(), "FINAL_BILL");

        authService.recordAuditLog("SETTLE_BILL", "BILL", String.valueOf(bill.getId()),
                "Table " + order.getTableNumber() + " settled: Bill #" + bill.getBillNumber() + ", Total: Rs." + totalAmount + " via " + paymentMode,
                userId, name, role, ipAddress);

        response.put("success", true);
        response.put("message", "Table " + order.getTableNumber() + " Bill #" + bill.getBillNumber() + " settled successfully!");
        response.put("bill", billData);
        response.put("print_job", printRes);
        response.put("auto_print", true);
        return response;
    }

    @Transactional
    public Map<String, Object> clearTable(int tableNo, Long userId, String role, String name, String ipAddress) {
        Map<String, Object> response = new HashMap<>();
        List<Order> orders = orderRepository.findByOrderTypeAndStatusIn(
                "DINING", List.of("PLACED", "CONFIRMED", "PREPARING", "READY")
        ).stream().filter(o -> Objects.equals(o.getTableNumber(), tableNo)).collect(Collectors.toList());

        if (orders.isEmpty()) {
            response.put("success", false);
            response.put("error", "No active order on Table " + tableNo);
            return response;
        }

        for (Order o : orders) {
            o.setStatus("CANCELLED");
            o.setUpdatedAt(LocalDateTime.now());
            orderRepository.save(o);
        }

        diningTableRepository.findByTableNumber(tableNo).ifPresent(tbl -> {
            tbl.setStatus("VACANT");
            tbl.setCurrentOrderId(null);
            diningTableRepository.save(tbl);
        });

        authService.recordAuditLog("CANCEL_TABLE_TAB", "TABLE", String.valueOf(tableNo),
                "Cancelled active order on Table " + tableNo,
                userId, name, role, ipAddress);

        response.put("success", true);
        response.put("message", "Table " + tableNo + " order cancelled and table freed.");
        return response;
    }

    public List<Map<String, Object>> getRecentBills(int limit) {
        return posBillRepository.findByStatusOrderByIdDesc("COMPLETED")
                .stream().limit(limit).map(PosBill::toMap).collect(Collectors.toList());
    }

    public Optional<Map<String, Object>> getBillDetails(String identifier) {
        if (identifier.matches("\\d+")) {
            return posBillRepository.findById(Long.valueOf(identifier)).map(PosBill::toMap);
        }
        return posBillRepository.findByBillNumber(identifier).map(PosBill::toMap);
    }
}
