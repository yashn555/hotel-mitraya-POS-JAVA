package com.hotelmitraya.service;

import com.hotelmitraya.model.PosBill;
import com.hotelmitraya.model.PosBillItem;
import com.hotelmitraya.repository.*;
import org.springframework.stereotype.Service;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class ReportService {

    private final PosBillRepository posBillRepository;
    private final PosBillItemRepository posBillItemRepository;
    private final UserRepository userRepository;
    private final CategoryRepository categoryRepository;
    private final MenuItemRepository menuItemRepository;
    private final OrderRepository orderRepository;
    private final PrinterConfigRepository printerConfigRepository;

    public ReportService(
            PosBillRepository posBillRepository,
            PosBillItemRepository posBillItemRepository,
            UserRepository userRepository,
            CategoryRepository categoryRepository,
            MenuItemRepository menuItemRepository,
            OrderRepository orderRepository,
            PrinterConfigRepository printerConfigRepository) {
        this.posBillRepository = posBillRepository;
        this.posBillItemRepository = posBillItemRepository;
        this.userRepository = userRepository;
        this.categoryRepository = categoryRepository;
        this.menuItemRepository = menuItemRepository;
        this.orderRepository = orderRepository;
        this.printerConfigRepository = printerConfigRepository;
    }

    public Map<String, Object> getSalesSummary() {
        LocalDateTime todayStart = LocalDateTime.of(LocalDate.now(), LocalTime.MIN);
        LocalDateTime todayEnd = LocalDateTime.of(LocalDate.now(), LocalTime.MAX);

        List<PosBill> todayBills = posBillRepository.findByCreatedAtBetweenAndStatus(todayStart, todayEnd, "COMPLETED");

        double totalSales = 0.0;
        double cashSales = 0.0;
        double upiSales = 0.0;
        double cardSales = 0.0;
        double discountGiven = 0.0;

        for (PosBill b : todayBills) {
            double amt = b.getTotalAmount() != null ? b.getTotalAmount() : 0.0;
            totalSales += amt;
            if ("CASH".equalsIgnoreCase(b.getPaymentMode())) cashSales += amt;
            else if ("UPI".equalsIgnoreCase(b.getPaymentMode())) upiSales += amt;
            else if ("CARD".equalsIgnoreCase(b.getPaymentMode())) cardSales += amt;
            discountGiven += (b.getDiscount() != null ? b.getDiscount() : 0.0);
        }

        int billsCount = todayBills.size();
        long allTimeBills = posBillRepository.countByStatus("COMPLETED");
        Double allTimeRev = posBillRepository.sumTotalAmountByStatus("COMPLETED");
        double allTimeRevenue = allTimeRev != null ? allTimeRev : 0.0;

        Map<String, Object> todayMap = new HashMap<>();
        todayMap.put("total_sales", Math.round(totalSales * 100.0) / 100.0);
        todayMap.put("bills_count", billsCount);
        todayMap.put("cash_sales", Math.round(cashSales * 100.0) / 100.0);
        todayMap.put("upi_sales", Math.round(upiSales * 100.0) / 100.0);
        todayMap.put("card_sales", Math.round(cardSales * 100.0) / 100.0);
        todayMap.put("discount_given", Math.round(discountGiven * 100.0) / 100.0);
        todayMap.put("average_bill", billsCount > 0 ? Math.round((totalSales / billsCount) * 100.0) / 100.0 : 0.0);

        Map<String, Object> allTimeMap = new HashMap<>();
        allTimeMap.put("total_bills", allTimeBills);
        allTimeMap.put("total_revenue", Math.round(allTimeRevenue * 100.0) / 100.0);

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("today", todayMap);
        response.put("all_time", allTimeMap);
        return response;
    }

    public List<Map<String, Object>> getBestSellers(int limit) {
        List<Object[]> rawList = posBillItemRepository.findBestSellingItems();
        List<Map<String, Object>> result = new ArrayList<>();

        for (Object[] row : rawList) {
            Map<String, Object> itemMap = new HashMap<>();
            itemMap.put("item_name", row[0]);
            itemMap.put("total_qty", row[1] != null ? ((Number) row[1]).intValue() : 0);
            itemMap.put("total_revenue", row[2] != null ? Math.round(((Number) row[2]).doubleValue() * 100.0) / 100.0 : 0.0);
            result.add(itemMap);
            if (result.size() >= limit) break;
        }
        return result;
    }

    public Map<String, Object> exportDatabaseBackup() {
        Map<String, Object> backup = new HashMap<>();
        backup.put("system", "Hotel Mitraya Restaurant POS");
        backup.put("exported_at", LocalDateTime.now().toString());
        backup.put("users", userRepository.findAll().stream().map(u -> u.toMap()).collect(Collectors.toList()));
        backup.put("categories", categoryRepository.findAll().stream().map(c -> c.toMap()).collect(Collectors.toList()));
        backup.put("menu_items", menuItemRepository.findAll().stream().map(m -> m.toMap()).collect(Collectors.toList()));
        backup.put("pos_bills", posBillRepository.findAll().stream().limit(500).map(b -> b.toMap()).collect(Collectors.toList()));
        backup.put("orders", orderRepository.findAll().stream().limit(500).map(o -> o.toMap()).collect(Collectors.toList()));
        backup.put("printer_configs", printerConfigRepository.findAll().stream().map(p -> p.toMap()).collect(Collectors.toList()));
        return backup;
    }
}
