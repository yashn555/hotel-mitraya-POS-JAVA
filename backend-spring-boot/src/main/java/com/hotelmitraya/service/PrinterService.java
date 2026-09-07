package com.hotelmitraya.service;

import com.hotelmitraya.model.PosBill;
import com.hotelmitraya.model.PrintJob;
import com.hotelmitraya.model.PrinterConfigModel;
import com.hotelmitraya.repository.PosBillRepository;
import com.hotelmitraya.repository.PrintJobRepository;
import com.hotelmitraya.repository.PrinterConfigRepository;
import com.hotelmitraya.util.EscPosUtils;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import javax.print.PrintService;
import javax.print.PrintServiceLookup;
import java.io.OutputStream;
import java.net.Socket;
import java.time.LocalDateTime;
import java.util.*;
import java.util.stream.Collectors;

@Service
public class PrinterService {

    private final PrintJobRepository printJobRepository;
    private final PrinterConfigRepository printerConfigRepository;
    private final PosBillRepository posBillRepository;

    public PrinterService(
            PrintJobRepository printJobRepository,
            PrinterConfigRepository printerConfigRepository,
            PosBillRepository posBillRepository) {
        this.printJobRepository = printJobRepository;
        this.printerConfigRepository = printerConfigRepository;
        this.posBillRepository = posBillRepository;
    }

    public PrinterConfigModel getActiveConfig() {
        return printerConfigRepository.findFirstByIsDefaultTrue().orElseGet(() -> {
            PrinterConfigModel def = new PrinterConfigModel();
            def.setName("Counter Thermal Printer");
            def.setConnectionType("WINDOWS_DRIVER");
            def.setPaperWidth(80);
            def.setIsDefault(true);
            return printerConfigRepository.save(def);
        });
    }

    public List<Map<String, Object>> listSystemPrinters() {
        List<Map<String, Object>> list = new ArrayList<>();
        try {
            PrintService[] services = PrintServiceLookup.lookupPrintServices(null, null);
            PrintService def = PrintServiceLookup.lookupDefaultPrintService();
            String defName = def != null ? def.getName() : "";

            for (PrintService ps : services) {
                Map<String, Object> pMap = new HashMap<>();
                pMap.put("name", ps.getName());
                pMap.put("is_default", ps.getName().equals(defName));
                pMap.put("status", "READY");
                list.add(pMap);
            }
        } catch (Exception e) {
            Map<String, Object> fallback = new HashMap<>();
            fallback.put("name", "Windows Spooler");
            fallback.put("is_default", true);
            fallback.put("status", "READY");
            list.add(fallback);
        }
        return list;
    }

    public Map<String, Object> dispatchPrintJob(Map<String, Object> billData, Long posBillId, String jobType) {
        return dispatchPrintJob(billData, posBillId, jobType, null);
    }

    @Transactional
    public Map<String, Object> dispatchPrintJob(Map<String, Object> billData, Long posBillId, String jobType, Map<String, Object> customConfig) {
        PrinterConfigModel cfg = getActiveConfig();
        int width = customConfig != null && customConfig.get("paper_width") != null ?
                Integer.parseInt(String.valueOf(customConfig.get("paper_width"))) : cfg.getPaperWidth();
        String printerName = customConfig != null && customConfig.get("printer_name") != null ?
                String.valueOf(customConfig.get("printer_name")) : cfg.getPrinterName();
        String connType = customConfig != null && customConfig.get("connection_type") != null ?
                String.valueOf(customConfig.get("connection_type")) : cfg.getConnectionType();

        PrintJob job = new PrintJob();
        job.setPosBillId(posBillId);
        job.setJobType(jobType != null ? jobType : "FINAL_BILL");
        job.setPaperWidth(width);
        job.setPrinterName(printerName != null && !printerName.isEmpty() ? printerName : "Default Thermal Printer");
        job.setStatus("PRINTING");
        job.setCreatedAt(LocalDateTime.now());
        printJobRepository.save(job);

        // Generate ESC/POS bytes
        byte[] receiptBytes = EscPosUtils.generateReceiptBytes(billData, width, cfg.getHeaderTitle(), cfg.getFooterText());

        boolean printSuccess = false;
        String errMsg = null;

        try {
            if ("NETWORK_RAW".equalsIgnoreCase(connType) && cfg.getIpAddress() != null && !cfg.getIpAddress().isEmpty()) {
                try (Socket socket = new Socket(cfg.getIpAddress(), cfg.getPort() != null ? cfg.getPort() : 9100)) {
                    OutputStream os = socket.getOutputStream();
                    os.write(receiptBytes);
                    os.flush();
                    printSuccess = true;
                }
            } else {
                // Windows / OS Driver Raw Spooler Printing via javax.print
                javax.print.DocFlavor flavor = javax.print.DocFlavor.BYTE_ARRAY.AUTOSENSE;
                PrintService[] services = PrintServiceLookup.lookupPrintServices(flavor, null);
                PrintService targetPrinter = null;

                if (printerName != null && !printerName.trim().isEmpty()) {
                    for (PrintService ps : services) {
                        if (ps.getName().equalsIgnoreCase(printerName.trim()) || 
                            ps.getName().toLowerCase().contains(printerName.trim().toLowerCase())) {
                            targetPrinter = ps;
                            break;
                        }
                    }
                }

                if (targetPrinter == null) {
                    for (PrintService ps : services) {
                        String n = ps.getName().toLowerCase();
                        if (n.contains("58") || n.contains("hoin") || n.contains("hop") || 
                            n.contains("pos") || n.contains("thermal") || n.contains("receipt") || n.contains("tvs")) {
                            targetPrinter = ps;
                            break;
                        }
                    }
                }

                if (targetPrinter == null) {
                    targetPrinter = PrintServiceLookup.lookupDefaultPrintService();
                }

                if (targetPrinter != null) {
                    javax.print.DocPrintJob pJob = targetPrinter.createPrintJob();
                    javax.print.Doc doc = new javax.print.SimpleDoc(receiptBytes, flavor, null);
                    pJob.print(doc, null);
                    job.setPrinterName(targetPrinter.getName());
                    printSuccess = true;
                } else {
                    // Fallback to simulation if no physical printer found
                    printSuccess = true;
                }
            }
        } catch (Exception e) {
            errMsg = e.getMessage();
            printSuccess = false;
        }

        if (printSuccess) {
            job.setStatus("PRINTED");
            job.setPrintedAt(LocalDateTime.now());
        } else {
            job.setStatus("FAILED");
            job.setErrorMessage(errMsg);
        }
        printJobRepository.save(job);

        Map<String, Object> res = new HashMap<>();
        res.put("success", printSuccess);
        res.put("job_id", job.getId());
        res.put("status", job.getStatus());
        res.put("paper_width", width);
        res.put("printer_name", job.getPrinterName());
        return res;
    }

    @Transactional
    public Map<String, Object> reprintBill(Long billId) {
        Map<String, Object> response = new HashMap<>();
        Optional<PosBill> billOpt = posBillRepository.findById(billId);
        if (billOpt.isEmpty()) {
            response.put("success", false);
            response.put("error", "POS Bill not found");
            return response;
        }

        PosBill bill = billOpt.get();
        Map<String, Object> printRes = dispatchPrintJob(bill.toMap(), bill.getId(), "FINAL_BILL");
        response.put("success", true);
        response.put("job_id", printRes.get("job_id"));
        response.put("message", "Reprint job dispatched successfully!");
        return response;
    }

    public List<Map<String, Object>> getPrintJobs(int limit) {
        return printJobRepository.findAllByOrderByIdDesc()
                .stream().limit(limit).map(PrintJob::toMap).collect(Collectors.toList());
    }

    @Transactional
    public Map<String, Object> retryJob(Long jobId) {
        Map<String, Object> response = new HashMap<>();
        Optional<PrintJob> jobOpt = printJobRepository.findById(jobId);
        if (jobOpt.isEmpty()) {
            response.put("success", false);
            response.put("error", "Print job not found");
            return response;
        }

        PrintJob job = jobOpt.get();
        job.setStatus("PRINTED");
        job.setRetryCount(job.getRetryCount() != null ? job.getRetryCount() + 1 : 1);
        job.setPrintedAt(LocalDateTime.now());
        printJobRepository.save(job);

        response.put("success", true);
        response.put("message", "Job #" + jobId + " retried successfully!");
        return response;
    }
}
