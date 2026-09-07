package com.hotelmitraya;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableScheduling;

@SpringBootApplication
@EnableScheduling
public class HotelMitrayaApplication {

    public static void main(String[] args) {
        SpringApplication.run(HotelMitrayaApplication.class, args);
        System.out.println("=================================================================");
        System.out.println("  Hotel Mitraya Restaurant POS & Billing Server Started (Port 5055)");
        System.out.println("  - Web Admin:     http://localhost:5055/admin");
        System.out.println("  - Cashier POS:   http://localhost:5055/pos");
        System.out.println("  - Waiter App:    http://localhost:5055/waiter");
        System.out.println("  - Kitchen KDS:   http://localhost:5055/kitchen");
        System.out.println("  - REST API Root: http://localhost:5055/api");
        System.out.println("=================================================================");
    }
}
