package com.hotelmitraya.service;

import com.hotelmitraya.util.CurrencyUtils;
import com.lowagie.text.*;
import com.lowagie.text.pdf.*;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import java.awt.Color;
import java.io.File;
import java.io.FileOutputStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.List;

@Service
public class BillPdfService {

    @Value("${bills.directory:bills}")
    private String billsDirectory;

    public File getBillsFolder() {
        File folder = new File(billsDirectory);
        if (!folder.isAbsolute()) {
            folder = new File(System.getProperty("user.dir"), billsDirectory);
        }
        if (!folder.exists()) {
            folder.mkdirs();
        }
        return folder;
    }

    public synchronized String getNextSequentialBillNumber() {
        File folder = getBillsFolder();
        File[] files = folder.listFiles((dir, name) -> name.toLowerCase().endsWith(".pdf"));
        int maxNo = 1000;
        if (files != null) {
            for (File f : files) {
                String name = f.getName().replace(".pdf", "");
                int lastUnderscore = name.lastIndexOf("_");
                if (lastUnderscore != -1) {
                    String part = name.substring(lastUnderscore + 1);
                    if (part.matches("\\d+")) {
                        try {
                            maxNo = Math.max(maxNo, Integer.parseInt(part));
                        } catch (Exception ignored) {}
                    }
                }
            }
        }
        return String.valueOf(maxNo + 1);
    }

    public Map<String, Object> generateBillPdf(Map<String, Object> payload) throws Exception {
        String customerName = String.valueOf(payload.getOrDefault("customer_name", "Customer")).trim();
        String billNo = String.valueOf(payload.getOrDefault("bill_no", "1001")).trim();
        String billDate = String.valueOf(payload.getOrDefault("bill_date", LocalDateToString(LocalDateTime.now()))).trim();
        String createdOn = String.valueOf(payload.getOrDefault("created_on", LocalDateTimeToString(LocalDateTime.now()))).trim();
        String txnMode = String.valueOf(payload.getOrDefault("txn_mode", "CASH")).trim().toUpperCase();
        double discount = Double.parseDouble(String.valueOf(payload.getOrDefault("discount", 0.0)));

        @SuppressWarnings("unchecked")
        List<Map<String, Object>> items = (List<Map<String, Object>>) payload.get("items");
        if (items == null || items.isEmpty()) {
            throw new IllegalArgumentException("At least one item is required");
        }

        String safeCustomer = customerName.replaceAll("[^a-zA-Z0-9\\s]", "").replace(" ", "_");
        String safeBillNo = billNo.replaceAll("[^a-zA-Z0-9]", "");
        String filename = safeCustomer + "_" + safeBillNo + ".pdf";

        File billsFolder = getBillsFolder();
        File outputFile = new File(billsFolder, filename);

        // Calculate totals
        double subtotal = 0.0;
        List<Map<String, Object>> processedItems = new ArrayList<>();
        int srNo = 1;

        for (Map<String, Object> itm : items) {
            String iname = String.valueOf(itm.get("name")).trim();
            double qty = Double.parseDouble(String.valueOf(itm.getOrDefault("qty", 1.0)));
            double rate = Double.parseDouble(String.valueOf(itm.getOrDefault("rate", 0.0)));
            double lineTotal = Math.round(qty * rate * 100.0) / 100.0;
            subtotal += lineTotal;

            Map<String, Object> row = new HashMap<>();
            row.put("sr", srNo++);
            row.put("name", iname);
            row.put("qty", (long) qty == qty ? String.valueOf((long) qty) : String.format("%.2f", qty));
            row.put("rate", String.format("%.2f", rate));
            row.put("amount", String.format("%.2f", lineTotal));
            processedItems.add(row);
        }

        subtotal = Math.round(subtotal * 100.0) / 100.0;
        discount = Math.min(discount, subtotal);
        double grandTotal = Math.max(0.0, Math.round((subtotal - discount) * 100.0) / 100.0);
        String amountInWords = CurrencyUtils.numberToWordsIndian(grandTotal);

        // Generate OpenPDF Document
        Document document = new Document(PageSize.A4, 36, 36, 36, 36);
        PdfWriter writer = PdfWriter.getInstance(document, new FileOutputStream(outputFile));
        document.open();

        // Colors
        Color primaryAmber = new Color(217, 119, 6);
        Color slateDark = new Color(15, 23, 42);
        Color grayLight = new Color(241, 245, 249);
        Color grayBorder = new Color(203, 213, 225);

        // Fonts
        Font titleFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 22, primaryAmber);
        Font subtitleFont = FontFactory.getFont(FontFactory.HELVETICA, 10, slateDark);
        Font boldFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, slateDark);
        Font regularFont = FontFactory.getFont(FontFactory.HELVETICA, 10, slateDark);
        Font headerFont = FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, Color.WHITE);

        // Header Table
        PdfPTable headerTable = new PdfPTable(2);
        headerTable.setWidthPercentage(100);
        headerTable.setWidths(new float[]{60, 40});

        PdfPCell hotelCell = new PdfPCell();
        hotelCell.setBorder(Rectangle.NO_BORDER);
        hotelCell.addElement(new Paragraph("HOTEL MITRAYA", titleFont));
        hotelCell.addElement(new Paragraph("Pure Veg Restaurant & Fast Food", subtitleFont));
        hotelCell.addElement(new Paragraph("Near Main Road, Pandharpur - 413304 | Tel: +91 9876543210", subtitleFont));
        headerTable.addCell(hotelCell);

        PdfPCell invMetaCell = new PdfPCell();
        invMetaCell.setBorder(Rectangle.NO_BORDER);
        invMetaCell.setHorizontalAlignment(Element.ALIGN_RIGHT);
        Paragraph invTitle = new Paragraph("TAX INVOICE / BILL", FontFactory.getFont(FontFactory.HELVETICA_BOLD, 14, primaryAmber));
        invTitle.setAlignment(Element.ALIGN_RIGHT);
        invMetaCell.addElement(invTitle);
        Paragraph pBillNo = new Paragraph("Bill No: " + billNo, boldFont);
        pBillNo.setAlignment(Element.ALIGN_RIGHT);
        invMetaCell.addElement(pBillNo);
        Paragraph pBillDate = new Paragraph("Date: " + billDate, regularFont);
        pBillDate.setAlignment(Element.ALIGN_RIGHT);
        invMetaCell.addElement(pBillDate);
        headerTable.addCell(invMetaCell);

        document.add(headerTable);
        document.add(new Paragraph(" "));

        // Customer Info Bar
        PdfPTable custTable = new PdfPTable(2);
        custTable.setWidthPercentage(100);
        custTable.setWidths(new float[]{50, 50});

        PdfPCell c1 = new PdfPCell(new Phrase("Customer: " + customerName, boldFont));
        c1.setBackgroundColor(grayLight);
        c1.setBorderColor(grayBorder);
        c1.setPadding(6);
        custTable.addCell(c1);

        PdfPCell c2 = new PdfPCell(new Phrase("Payment Mode: " + txnMode, boldFont));
        c2.setBackgroundColor(grayLight);
        c2.setBorderColor(grayBorder);
        c2.setHorizontalAlignment(Element.ALIGN_RIGHT);
        c2.setPadding(6);
        custTable.addCell(c2);

        document.add(custTable);
        document.add(new Paragraph(" "));

        // Items Table
        PdfPTable itemsTable = new PdfPTable(5);
        itemsTable.setWidthPercentage(100);
        itemsTable.setWidths(new float[]{8, 52, 12, 14, 14});

        String[] headers = {"Sr.", "Description / Particulars", "Qty", "Rate (Rs)", "Amount (Rs)"};
        for (String h : headers) {
            PdfPCell hCell = new PdfPCell(new Phrase(h, headerFont));
            hCell.setBackgroundColor(primaryAmber);
            hCell.setBorderColor(primaryAmber);
            hCell.setPadding(6);
            if (h.contains("Qty") || h.contains("Rate") || h.contains("Amount")) {
                hCell.setHorizontalAlignment(Element.ALIGN_RIGHT);
            } else if (h.contains("Sr.")) {
                hCell.setHorizontalAlignment(Element.ALIGN_CENTER);
            }
            itemsTable.addCell(hCell);
        }

        for (Map<String, Object> itm : processedItems) {
            PdfPCell srCell = new PdfPCell(new Phrase(String.valueOf(itm.get("sr")), regularFont));
            srCell.setHorizontalAlignment(Element.ALIGN_CENTER);
            srCell.setPadding(6);
            srCell.setBorderColor(grayBorder);
            itemsTable.addCell(srCell);

            PdfPCell nameCell = new PdfPCell(new Phrase(String.valueOf(itm.get("name")), regularFont));
            nameCell.setPadding(6);
            nameCell.setBorderColor(grayBorder);
            itemsTable.addCell(nameCell);

            PdfPCell qtyCell = new PdfPCell(new Phrase(String.valueOf(itm.get("qty")), regularFont));
            qtyCell.setHorizontalAlignment(Element.ALIGN_RIGHT);
            qtyCell.setPadding(6);
            qtyCell.setBorderColor(grayBorder);
            itemsTable.addCell(qtyCell);

            PdfPCell rateCell = new PdfPCell(new Phrase(String.valueOf(itm.get("rate")), regularFont));
            rateCell.setHorizontalAlignment(Element.ALIGN_RIGHT);
            rateCell.setPadding(6);
            rateCell.setBorderColor(grayBorder);
            itemsTable.addCell(rateCell);

            PdfPCell amtCell = new PdfPCell(new Phrase(String.valueOf(itm.get("amount")), regularFont));
            amtCell.setHorizontalAlignment(Element.ALIGN_RIGHT);
            amtCell.setPadding(6);
            amtCell.setBorderColor(grayBorder);
            itemsTable.addCell(amtCell);
        }

        // Totals Rows
        PdfPCell totalLabelCell = new PdfPCell(new Phrase("Subtotal:", boldFont));
        totalLabelCell.setColspan(4);
        totalLabelCell.setHorizontalAlignment(Element.ALIGN_RIGHT);
        totalLabelCell.setPadding(6);
        totalLabelCell.setBorderColor(grayBorder);
        itemsTable.addCell(totalLabelCell);

        PdfPCell subValCell = new PdfPCell(new Phrase(String.format("Rs. %.2f", subtotal), boldFont));
        subValCell.setHorizontalAlignment(Element.ALIGN_RIGHT);
        subValCell.setPadding(6);
        subValCell.setBorderColor(grayBorder);
        itemsTable.addCell(subValCell);

        if (discount > 0) {
            PdfPCell discLabel = new PdfPCell(new Phrase("Discount:", boldFont));
            discLabel.setColspan(4);
            discLabel.setHorizontalAlignment(Element.ALIGN_RIGHT);
            discLabel.setPadding(6);
            discLabel.setBorderColor(grayBorder);
            itemsTable.addCell(discLabel);

            PdfPCell discVal = new PdfPCell(new Phrase(String.format("-Rs. %.2f", discount), boldFont));
            discVal.setHorizontalAlignment(Element.ALIGN_RIGHT);
            discVal.setPadding(6);
            discVal.setBorderColor(grayBorder);
            itemsTable.addCell(discVal);
        }

        PdfPCell grandLabel = new PdfPCell(new Phrase("GRAND TOTAL:", FontFactory.getFont(FontFactory.HELVETICA_BOLD, 11, primaryAmber)));
        grandLabel.setColspan(4);
        grandLabel.setHorizontalAlignment(Element.ALIGN_RIGHT);
        grandLabel.setPadding(6);
        grandLabel.setBackgroundColor(grayLight);
        grandLabel.setBorderColor(grayBorder);
        itemsTable.addCell(grandLabel);

        PdfPCell grandVal = new PdfPCell(new Phrase(String.format("Rs. %.2f", grandTotal), FontFactory.getFont(FontFactory.HELVETICA_BOLD, 11, primaryAmber)));
        grandVal.setHorizontalAlignment(Element.ALIGN_RIGHT);
        grandVal.setPadding(6);
        grandVal.setBackgroundColor(grayLight);
        grandVal.setBorderColor(grayBorder);
        itemsTable.addCell(grandVal);

        document.add(itemsTable);
        document.add(new Paragraph(" "));

        // Amount in Words Bar
        PdfPTable wordsTable = new PdfPTable(1);
        wordsTable.setWidthPercentage(100);
        PdfPCell wordsCell = new PdfPCell(new Phrase("Amount in Words: " + amountInWords, boldFont));
        wordsCell.setBackgroundColor(grayLight);
        wordsCell.setBorderColor(grayBorder);
        wordsCell.setPadding(6);
        wordsTable.addCell(wordsCell);
        document.add(wordsTable);

        // Footer Note
        document.add(new Paragraph(" "));
        Paragraph footerPara = new Paragraph("Thank You! Visit Again.", FontFactory.getFont(FontFactory.HELVETICA_BOLD, 10, primaryAmber));
        footerPara.setAlignment(Element.ALIGN_CENTER);
        document.add(footerPara);

        document.close();
        writer.close();

        Map<String, Object> meta = getBillMetadata(filename);
        meta.put("filepath", outputFile.getAbsolutePath());
        return meta;
    }

    public Map<String, Object> getBillMetadata(String filename) {
        File folder = getBillsFolder();
        File file = new File(folder, filename);
        if (!file.exists()) {
            return null;
        }
        long sizeBytes = file.length();
        double sizeKb = Math.round((sizeBytes / 1024.0) * 10.0) / 10.0;
        long mtime = file.lastModified();

        String nameNoExt = filename.replace(".pdf", "");
        String custDisplay = nameNoExt.replace("_", " ");
        String billNoDisplay = "N/A";
        int lastUnderscore = nameNoExt.lastIndexOf("_");
        if (lastUnderscore != -1) {
            custDisplay = nameNoExt.substring(0, lastUnderscore).replace("_", " ");
            billNoDisplay = nameNoExt.substring(lastUnderscore + 1);
        }

        Map<String, Object> meta = new HashMap<>();
        meta.put("filename", filename);
        meta.put("customer_name", custDisplay);
        meta.put("bill_no", billNoDisplay);
        meta.put("size_bytes", sizeBytes);
        meta.put("size_kb", sizeKb);
        meta.put("created_at", new Date(mtime).toString());
        meta.put("timestamp", mtime);
        meta.put("download_url", "/api/bills/download/" + filename);
        meta.put("preview_url", "/api/bills/preview/" + filename);
        return meta;
    }

    public List<Map<String, Object>> listBills(String searchQuery) {
        File folder = getBillsFolder();
        File[] files = folder.listFiles((dir, name) -> name.toLowerCase().endsWith(".pdf") && !name.startsWith("."));
        List<Map<String, Object>> bills = new ArrayList<>();
        if (files != null) {
            for (File f : files) {
                Map<String, Object> meta = getBillMetadata(f.getName());
                if (meta != null) {
                    if (searchQuery != null && !searchQuery.trim().isEmpty()) {
                        String q = searchQuery.trim().toLowerCase();
                        String cust = String.valueOf(meta.get("customer_name")).toLowerCase();
                        String bno = String.valueOf(meta.get("bill_no")).toLowerCase();
                        String fname = String.valueOf(meta.get("filename")).toLowerCase();
                        if (cust.contains(q) || bno.contains(q) || fname.contains(q)) {
                            bills.add(meta);
                        }
                    } else {
                        bills.add(meta);
                    }
                }
            }
        }
        bills.sort((a, b) -> Long.compare((Long) b.get("timestamp"), (Long) a.get("timestamp")));
        return bills;
    }

    public boolean deleteBill(String filename) {
        File folder = getBillsFolder();
        File file = new File(folder, filename);
        if (file.exists() && file.isFile()) {
            return file.delete();
        }
        return false;
    }

    private String LocalDateToString(LocalDateTime dt) {
        return dt.format(DateTimeFormatter.ofPattern("dd/MM/yyyy"));
    }

    private String LocalDateTimeToString(LocalDateTime dt) {
        return dt.format(DateTimeFormatter.ofPattern("dd/MM/yyyy hh:mm a"));
    }
}
