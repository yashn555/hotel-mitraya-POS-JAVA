package com.hotelmitraya.controller;

import jakarta.servlet.http.HttpSession;
import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestMethod;

@Controller
public class WebViewController {

    @GetMapping("/")
    public String index(HttpSession session) {
        if (session != null && Boolean.TRUE.equals(session.getAttribute("authenticated"))) {
            String role = session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "admin";
            if ("waiter".equalsIgnoreCase(role)) {
                return "redirect:/waiter";
            } else if ("cashier".equalsIgnoreCase(role)) {
                return "redirect:/pos";
            }
            return "redirect:/admin";
        }
        return "login";
    }

    @GetMapping("/login")
    public String loginPage(HttpSession session) {
        if (session != null && Boolean.TRUE.equals(session.getAttribute("authenticated"))) {
            String role = session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "admin";
            if ("waiter".equalsIgnoreCase(role)) {
                return "redirect:/waiter";
            } else if ("cashier".equalsIgnoreCase(role)) {
                return "redirect:/pos";
            }
            return "redirect:/admin";
        }
        return "login";
    }

    @GetMapping("/admin")
    public String adminDashboard(HttpSession session, Model model) {
        model.addAttribute("user_name", session != null && session.getAttribute("user_name") != null ? session.getAttribute("user_name") : "Admin");
        return "admin_dashboard";
    }

    @GetMapping("/admin/menu")
    public String menuManagement(HttpSession session, Model model) {
        model.addAttribute("user_name", session != null && session.getAttribute("user_name") != null ? session.getAttribute("user_name") : "Admin");
        return "menu_management";
    }

    @GetMapping("/admin/reports")
    public String salesReports(HttpSession session, Model model) {
        model.addAttribute("user_name", session != null && session.getAttribute("user_name") != null ? session.getAttribute("user_name") : "Admin");
        return "sales_reports";
    }

    @GetMapping("/pos")
    public String posCounter(HttpSession session, Model model) {
        model.addAttribute("user_role", session != null && session.getAttribute("role") != null ? session.getAttribute("role") : "cashier");
        model.addAttribute("user_name", session != null && session.getAttribute("user_name") != null ? session.getAttribute("user_name") : "Staff");
        return "pos";
    }

    @GetMapping("/waiter")
    public String waiterApp(HttpSession session, Model model) {
        model.addAttribute("user_name", session != null && session.getAttribute("user_name") != null ? session.getAttribute("user_name") : "Waiter");
        model.addAttribute("user_role", session != null && session.getAttribute("role") != null ? session.getAttribute("role") : "waiter");
        return "waiter";
    }

    @GetMapping({"/kitchen", "/kds"})
    public String kitchenScreen(HttpSession session, Model model) {
        model.addAttribute("user_role", session != null && session.getAttribute("role") != null ? session.getAttribute("role") : "staff");
        model.addAttribute("user_name", session != null && session.getAttribute("user_name") != null ? session.getAttribute("user_name") : "Kitchen Staff");
        return "kitchen";
    }

    @GetMapping("/display")
    public String displayScreen(HttpSession session, Model model) {
        model.addAttribute("user_role", session != null && session.getAttribute("role") != null ? session.getAttribute("role") : "cashier");
        model.addAttribute("user_name", session != null && session.getAttribute("user_name") != null ? session.getAttribute("user_name") : "Staff");
        return "display";
    }

    @GetMapping("/bulk")
    public String bulkBilling(HttpSession session, Model model) {
        model.addAttribute("user_role", session != null && session.getAttribute("role") != null ? session.getAttribute("role") : "admin");
        return "index";
    }

    @RequestMapping(value = "/logout", method = {RequestMethod.GET, RequestMethod.POST})
    public String logoutPage(HttpSession session) {
        if (session != null) {
            session.invalidate();
        }
        return "redirect:/login";
    }
}
