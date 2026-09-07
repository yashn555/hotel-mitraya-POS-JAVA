package com.hotelmitraya.pos.printer;

import android.bluetooth.BluetoothAdapter;
import android.bluetooth.BluetoothDevice;
import android.bluetooth.BluetoothSocket;
import com.hotelmitraya.pos.model.PosBillModel;

import java.io.ByteArrayOutputStream;
import java.io.OutputStream;
import java.nio.charset.StandardCharsets;
import java.util.UUID;

public class EscPosPrinterHelper {

    private static final UUID SPP_UUID = UUID.fromString("00001101-0000-1000-8000-00805F9B34FB");

    public static boolean printReceiptBluetooth(String bluetoothAddress, PosBillModel bill, int paperWidth) {
        if (bluetoothAddress == null || bluetoothAddress.isEmpty()) return false;
        BluetoothAdapter adapter = BluetoothAdapter.getDefaultAdapter();
        if (adapter == null || !adapter.isEnabled()) return false;

        try {
            BluetoothDevice device = adapter.getRemoteDevice(bluetoothAddress);
            try (BluetoothSocket socket = device.createRfcommSocketToServiceRecord(SPP_UUID)) {
                socket.connect();
                OutputStream os = socket.getOutputStream();

                byte[] receiptBytes = formatReceipt(bill, paperWidth);
                os.write(receiptBytes);
                os.flush();
                return true;
            }
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
    }

    public static byte[] formatReceipt(PosBillModel bill, int paperWidth) {
        ByteArrayOutputStream out = new ByteArrayOutputStream();
        int cols = paperWidth == 58 ? 32 : 48;

        try {
            out.write(new byte[]{0x1B, 0x40}); // INIT
            out.write(new byte[]{0x1B, 0x61, 0x01}); // Center
            out.write("HOTEL MITRAYA\n".getBytes(StandardCharsets.UTF_8));
            out.write("Pure Veg Restaurant & Fast Food\n".getBytes(StandardCharsets.UTF_8));
            out.write("--------------------------------\n".getBytes(StandardCharsets.UTF_8));

            out.write(new byte[]{0x1B, 0x61, 0x00}); // Left
            out.write(("Bill No: " + bill.getBillNumber() + "\n").getBytes(StandardCharsets.UTF_8));
            out.write(("Type: " + bill.getOrderType() + " (" + bill.getTableLabel() + ")\n").getBytes(StandardCharsets.UTF_8));
            out.write(("Total: Rs. " + String.format("%.2f", bill.getTotalAmount()) + "\n").getBytes(StandardCharsets.UTF_8));
            out.write("--------------------------------\n".getBytes(StandardCharsets.UTF_8));

            out.write(new byte[]{0x1B, 0x61, 0x01}); // Center
            out.write("Thank You! Visit Again.\n\n\n".getBytes(StandardCharsets.UTF_8));
            out.write(new byte[]{0x1D, 0x56, 0x41, 0x03}); // Cut
        } catch (Exception ignored) {}

        return out.toByteArray();
    }
}
