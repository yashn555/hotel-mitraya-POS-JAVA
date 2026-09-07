package com.hotelmitraya.service;

import com.hotelmitraya.model.Category;
import com.hotelmitraya.model.DiningTable;
import com.hotelmitraya.model.MenuItem;
import com.hotelmitraya.model.PrinterConfigModel;
import com.hotelmitraya.model.User;
import com.hotelmitraya.repository.CategoryRepository;
import com.hotelmitraya.repository.DiningTableRepository;
import com.hotelmitraya.repository.MenuItemRepository;
import com.hotelmitraya.repository.PrinterConfigRepository;
import com.hotelmitraya.repository.UserRepository;
import com.hotelmitraya.util.SecurityUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;

@Service
public class DatabaseSeeder implements CommandLineRunner {

    private final UserRepository userRepository;
    private final CategoryRepository categoryRepository;
    private final MenuItemRepository menuItemRepository;
    private final DiningTableRepository diningTableRepository;
    private final PrinterConfigRepository printerConfigRepository;

    @Value("${admin.pin:2005}")
    private String adminPin;

    @Value("${cashier.pin:5678}")
    private String cashierPin;

    @Value("${waiter.pin:1234}")
    private String waiterPin;

    public DatabaseSeeder(
            UserRepository userRepository,
            CategoryRepository categoryRepository,
            MenuItemRepository menuItemRepository,
            DiningTableRepository diningTableRepository,
            PrinterConfigRepository printerConfigRepository) {
        this.userRepository = userRepository;
        this.categoryRepository = categoryRepository;
        this.menuItemRepository = menuItemRepository;
        this.diningTableRepository = diningTableRepository;
        this.printerConfigRepository = printerConfigRepository;
    }

    @Override
    @Transactional
    public void run(String... args) {
        seedUsers();
        seedPrinterConfig();
        seedDiningTables();
        seedMenuCatalog();
    }

    private void seedUsers() {
        if (userRepository.findByUsername("admin").isEmpty()) {
            userRepository.save(new User("admin", "admin", SecurityUtils.hashPin(adminPin), "Hotel Admin"));
        }
        if (userRepository.findByUsername("cashier").isEmpty()) {
            userRepository.save(new User("cashier", "cashier", SecurityUtils.hashPin(cashierPin), "Counter Cashier"));
        }
        if (userRepository.findByUsername("waiter").isEmpty()) {
            userRepository.save(new User("waiter", "waiter", SecurityUtils.hashPin(waiterPin), "Floor Waiter"));
        }
    }

    private void seedPrinterConfig() {
        if (printerConfigRepository.findFirstByIsDefaultTrue().isEmpty()) {
            PrinterConfigModel config = new PrinterConfigModel();
            config.setName("HOIN HOP-H58 58mm Thermal Printer");
            config.setPrinterName("HOIN HOP-H58");
            config.setConnectionType("WINDOWS_DRIVER");
            config.setPaperWidth(58);
            config.setIsDefault(true);
            config.setCutEnabled(true);
            config.setHeaderTitle("HOTEL MITRAYA");
            config.setFooterText("Thank You! Visit Again.");
            printerConfigRepository.save(config);
        }
    }

    private void seedDiningTables() {
        if (diningTableRepository.count() == 0) {
            for (int t = 1; t <= 12; t++) {
                diningTableRepository.save(new DiningTable(t, 4, "VACANT"));
            }
        }
    }

    private void seedMenuCatalog() {
        if (categoryRepository.count() == 0) {
            // Category 1: Special Dishes
            Category cat1 = categoryRepository.save(new Category("Special Dishes", 1));
            menuItemRepository.saveAll(List.of(
                new MenuItem(cat1, "Dahi Dhapata & Biryani Plate", 130.0, "SP01", 1),
                new MenuItem(cat1, "Special Veg Thali", 160.0, "SP02", 2),
                new MenuItem(cat1, "Deluxe Thali (Sweet + Papad)", 200.0, "SP03", 3),
                new MenuItem(cat1, "Special Dahi Dhapata (2 Pcs)", 110.0, "SP04", 4)
            ));

            // Category 2: Main Course & Rice
            Category cat2 = categoryRepository.save(new Category("Main Course & Rice", 2));
            menuItemRepository.saveAll(List.of(
                new MenuItem(cat2, "Veg Dum Biryani", 140.0, "RC01", 1),
                new MenuItem(cat2, "Jeera Rice & Dal Tadka Combo", 130.0, "RC02", 2),
                new MenuItem(cat2, "Paneer Butter Masala", 150.0, "RC03", 3),
                new MenuItem(cat2, "Kaju Curry", 180.0, "RC04", 4),
                new MenuItem(cat2, "Butter Roti / Chapati (2 Pcs)", 30.0, "RC05", 5)
            ));

            // Category 3: Breakfast & Snacks
            Category cat3 = categoryRepository.save(new Category("Breakfast & Snacks", 3));
            menuItemRepository.saveAll(List.of(
                new MenuItem(cat3, "Special Misal Pav", 80.0, "SN01", 1),
                new MenuItem(cat3, "Poha with Sev & Lime", 40.0, "SN02", 2),
                new MenuItem(cat3, "Upma / Sheera", 45.0, "SN03", 3),
                new MenuItem(cat3, "Batata Vada Sambar (2 Pcs)", 50.0, "SN04", 4),
                new MenuItem(cat3, "Idli Sambar (2 Pcs)", 50.0, "SN05", 5),
                new MenuItem(cat3, "Medu Vada (2 Pcs)", 60.0, "SN06", 6),
                new MenuItem(cat3, "Masala Dosa", 75.0, "SN07", 7)
            ));

            // Category 4: Beverages & Drinks
            Category cat4 = categoryRepository.save(new Category("Beverages & Drinks", 4));
            menuItemRepository.saveAll(List.of(
                new MenuItem(cat4, "Special Masala Chai", 20.0, "BV01", 1),
                new MenuItem(cat4, "South Indian Filter Coffee", 30.0, "BV02", 2),
                new MenuItem(cat4, "Fresh Sweet Lassi", 50.0, "BV03", 3),
                new MenuItem(cat4, "Taak / Spiced Buttermilk", 25.0, "BV04", 4),
                new MenuItem(cat4, "Mineral Water Bottle (1L)", 20.0, "BV05", 5)
            ));

            // Category 5: Desserts & Sweets
            Category cat5 = categoryRepository.save(new Category("Desserts & Sweets", 5));
            menuItemRepository.saveAll(List.of(
                new MenuItem(cat5, "Gulab Jamun (2 Pcs)", 50.0, "DS01", 1),
                new MenuItem(cat5, "Shrikhand Bowl", 60.0, "DS02", 2),
                new MenuItem(cat5, "Ice Cream Scoop", 40.0, "DS03", 3)
            ));
        }
    }
}
