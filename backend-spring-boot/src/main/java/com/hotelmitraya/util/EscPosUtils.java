package com.hotelmitraya.util;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;

public class EscPosUtils {

    public static final byte[] INIT = {0x1B, 0x40};
    public static final byte[] ALIGN_CENTER = {0x1B, 0x61, 0x01};
    public static final byte[] ALIGN_LEFT = {0x1B, 0x61, 0x00};
    public static final byte[] ALIGN_RIGHT = {0x1B, 0x61, 0x02};
    public static final byte[] BOLD_ON = {0x1B, 0x45, 0x01};
    public static final byte[] BOLD_OFF = {0x1B, 0x45, 0x00};
    public static final byte[] DOUBLE_HEIGHT = {0x1B, 0x21, 0x10};
    public static final byte[] NORMAL_SIZE = {0x1B, 0x21, 0x00};
    public static final byte[] CUT_PAPER = {0x1D, 0x56, 0x41, 0x03};

    public static byte[] generateReceiptBytes(Map<String, Object> billData, int paperWidth, String headerTitle, String footerText) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        int cols = paperWidth == 58 ? 32 : 48;

        try {
            out.write(INIT);
            
            // Header
            out.write(ALIGN_CENTER);
            out.write(BOLD_ON);
            out.write(DOUBLE_HEIGHT);
            out.write(((headerTitle != null ? headerTitle : "HOTEL MITRAYA") + "\n").getBytes(StandardCharsets.UTF_8));
            out.write(NORMAL_SIZE);
            out.write(BOLD_OFF);
            out.write("Pure Veg Restaurant & Fast Food\n".getBytes(StandardCharsets.UTF_8));
            out.write("--------------------------------\n".getBytes(StandardCharsets.UTF_8));

            // Metadata
            out.write(ALIGN_LEFT);
            String billNo = String.valueOf(billData.getOrDefault("bill_number", "N/A"));
            String orderType = String.valueOf(billData.getOrDefault("order_type", "WALK_IN"));
            String tableLabel = String.valueOf(billData.getOrDefault("table_label", "Walk-in"));
            String dateStr = String.valueOf(billData.getOrDefault("created_at", ""));

            out.write(("Bill No: " + billNo + "\n").getBytes(StandardCharsets.UTF_8));
            out.write(("Type: " + orderType + " (" + tableLabel + ")\n").getBytes(StandardCharsets.UTF_8));
            if (!dateStr.isEmpty()) {
                out.write(("Date: " + dateStr + "\n").getBytes(StandardCharsets.UTF_8));
            }
            out.write("--------------------------------\n".getBytes(StandardCharsets.UTF_8));

            // Table Header
            out.write(BOLD_ON);
            out.write(formatColumns("Item", "Qty", "Amount", cols).getBytes(StandardCharsets.UTF_8));
            out.write(BOLD_OFF);
            out.write("--------------------------------\n".getBytes(StandardCharsets.UTF_8));

            // Items
            @SuppressWarnings("unchecked")
            List<Map<String, Object>> items = (List<Map<String, Object>>) billData.get("items");
            if (items != null) {
                for (Map<String, Object> item : items) {
                    String name = String.valueOf(item.getOrDefault("item_name", ""));
                    String qty = String.valueOf(item.getOrDefault("quantity", "1"));
                    double tot = Double.parseDouble(String.valueOf(item.getOrDefault("total_price", 0.0)));
                    out.write(formatColumns(name, qty, String.format("%.2f", tot), cols).getBytes(StandardCharsets.UTF_8));
                }
            }

            out.write("--------------------------------\n".getBytes(StandardCharsets.UTF_8));

            // Totals
            double subtotal = Double.parseDouble(String.valueOf(billData.getOrDefault("subtotal", 0.0)));
            double discount = Double.parseDouble(String.valueOf(billData.getOrDefault("discount", 0.0)));
            double total = Double.parseDouble(String.valueOf(billData.getOrDefault("total_amount", 0.0)));
            String payMode = String.valueOf(billData.getOrDefault("payment_mode", "CASH"));

            out.write(formatRow("Subtotal:", String.format("Rs. %.2f", subtotal), cols).getBytes(StandardCharsets.UTF_8));
            if (discount > 0) {
                out.write(formatRow("Discount:", String.format("-Rs. %.2f", discount), cols).getBytes(StandardCharsets.UTF_8));
            }
            out.write(BOLD_ON);
            out.write(formatRow("GRAND TOTAL:", String.format("Rs. %.2f", total), cols).getBytes(StandardCharsets.UTF_8));
            out.write(BOLD_OFF);
            out.write(formatRow("Payment Mode:", payMode, cols).getBytes(StandardCharsets.UTF_8));

            out.write("--------------------------------\n".getBytes(StandardCharsets.UTF_8));
            out.write(ALIGN_CENTER);
            out.write(((footerText != null ? footerText : "Thank You! Visit Again.") + "\n\n\n").getBytes(StandardCharsets.UTF_8));
            out.write(CUT_PAPER);

        } catch (IOException e) {
            e.printStackTrace();
        }

        return out.toByteArray();
    }

    private static String formatColumns(String col1, String col2, String col3, int totalWidth) {
        int w3 = 9;
        int w2 = 5;
        int w1 = totalWidth - w2 - w3;
        if (w1 < 10) w1 = 10;

        String c1 = col1.length() > w1 ? col1.substring(0, w1 - 1) : col1;
        return String.format("%-" + w1 + "s%" + w2 + "s%" + w3 + "s\n", c1, col2, col3);
    }

    private static String formatRow(String label, String value, int totalWidth) {
        int labelWidth = totalWidth - value.length();
        if (labelWidth < 1) labelWidth = 1;
        return String.format("%-" + labelWidth + "s%s\n", label, value);
    }
}
