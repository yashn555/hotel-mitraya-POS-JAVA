package com.hotelmitraya.controller;

import com.hotelmitraya.model.User;
import com.hotelmitraya.service.AuthService;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpSession;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;

@RestController
@CrossOrigin(origins = "*")
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @PostMapping({"/api/pos/login", "/api/auth/login", "/api/login"})
    public ResponseEntity<Map<String, Object>> login(
            @RequestBody(required = false) Map<String, Object> body,
            @RequestParam(required = false) Map<String, String> params,
            HttpServletRequest request,
            HttpSession session) {

        Map<String, Object> data = body != null ? body : (params != null ? new HashMap<>(params) : new HashMap<>());
        String enteredPin = String.valueOf(data.getOrDefault("pin", "")).trim();
        String requestedRole = String.valueOf(data.getOrDefault("role", "")).trim().toLowerCase();
        String clientIp = request.getRemoteAddr();

        if (enteredPin.isEmpty()) {
            Map<String, Object> err = new HashMap<>();
            err.put("success", false);
            err.put("error", "Please enter your security PIN");
            return ResponseEntity.badRequest().body(err);
        }

        Optional<User> userOpt = authService.authenticate(enteredPin, requestedRole, clientIp);
        if (userOpt.isEmpty()) {
            Map<String, Object> err = new HashMap<>();
            err.put("success", false);
            err.put("error", "Incorrect " + (!requestedRole.isEmpty() ? requestedRole.substring(0, 1).toUpperCase() + requestedRole.substring(1) + " " : "") + "PIN. Access denied.");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(err);
        }

        User user = userOpt.get();
        if (user.getIsActive() != null && !user.getIsActive()) {
            Map<String, Object> err = new HashMap<>();
            err.put("success", false);
            err.put("error", "User account is disabled or invalid");
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).body(err);
        }

        // Establish session
        session.setAttribute("authenticated", true);
        session.setAttribute("user_id", user.getId());
        session.setAttribute("username", user.getUsername());
        session.setAttribute("role", user.getRole());
        session.setAttribute("user_name", user.getName());

        String redirectTarget = "/pos";
        if ("admin".equalsIgnoreCase(user.getRole())) {
            redirectTarget = "/admin";
        } else if ("waiter".equalsIgnoreCase(user.getRole())) {
            redirectTarget = "/waiter";
        }

        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("role", user.getRole());
        response.put("name", user.getName());
        response.put("user_id", user.getId());
        response.put("username", user.getUsername());
        response.put("message", "Welcome " + user.getName() + "! Access granted.");
        response.put("redirect", redirectTarget);

        return ResponseEntity.ok(response);
    }

    @GetMapping({"/api/auth/me", "/api/pos/me"})
    public ResponseEntity<Map<String, Object>> getCurrentUser(HttpSession session) {
        Map<String, Object> response = new HashMap<>();
        boolean auth = session != null && Boolean.TRUE.equals(session.getAttribute("authenticated"));
        if (!auth) {
            response.put("authenticated", false);
            response.put("role", null);
            response.put("name", null);
            response.put("user_id", null);
            return ResponseEntity.ok(response);
        }

        response.put("authenticated", true);
        response.put("role", session.getAttribute("role"));
        response.put("name", session.getAttribute("user_name"));
        response.put("username", session.getAttribute("username"));
        response.put("user_id", session.getAttribute("user_id"));
        return ResponseEntity.ok(response);
    }

    @RequestMapping(value = {"/api/auth/logout", "/api/pos/logout", "/api/logout"}, method = {RequestMethod.GET, RequestMethod.POST})
    public ResponseEntity<Map<String, Object>> logout(HttpSession session) {
        if (session != null) {
            session.invalidate();
        }
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("message", "Logged out successfully");
        response.put("redirect", "/login");
        return ResponseEntity.ok(response);
    }

    @GetMapping("/api/admin/users")
    public ResponseEntity<Map<String, Object>> listUsers() {
        Map<String, Object> response = new HashMap<>();
        response.put("success", true);
        response.put("users", authService.getAllUsers());
        return ResponseEntity.ok(response);
    }

    @PostMapping("/api/admin/users")
    public ResponseEntity<Map<String, Object>> saveUser(
            @RequestBody Map<String, Object> data,
            HttpSession session,
            HttpServletRequest request) {

        Long userId = session != null && session.getAttribute("user_id") != null ? (Long) session.getAttribute("user_id") : null;
        String username = session != null && session.getAttribute("username") != null ? String.valueOf(session.getAttribute("username")) : "Admin";
        String role = session != null && session.getAttribute("role") != null ? String.valueOf(session.getAttribute("role")) : "admin";
        String ipAddress = request.getRemoteAddr();

        Map<String, Object> result = authService.saveUser(data, userId, username, role, ipAddress);
        if (Boolean.FALSE.equals(result.get("success"))) {
            return ResponseEntity.badRequest().body(result);
        }
        return ResponseEntity.ok(result);
    }
}
