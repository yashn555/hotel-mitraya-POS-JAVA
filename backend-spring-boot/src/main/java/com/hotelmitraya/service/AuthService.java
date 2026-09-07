package com.hotelmitraya.service;

import com.hotelmitraya.model.AuditLog;
import com.hotelmitraya.model.User;
import com.hotelmitraya.repository.AuditLogRepository;
import com.hotelmitraya.repository.UserRepository;
import com.hotelmitraya.util.SecurityUtils;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.stream.Collectors;

@Service
public class AuthService {

    private final UserRepository userRepository;
    private final AuditLogRepository auditLogRepository;

    @Value("${app.pin:2005}")
    private String appPin;

    public AuthService(UserRepository userRepository, AuditLogRepository auditLogRepository) {
        this.userRepository = userRepository;
        this.auditLogRepository = auditLogRepository;
    }

    public void recordAuditLog(String action, String entity, String entityId, String details,
                               Long userId, String username, String role, String ipAddress) {
        try {
            AuditLog log = new AuditLog(userId, username, role, action, entity, entityId, details, ipAddress);
            auditLogRepository.save(log);
        } catch (Exception e) {
            System.err.println("[WARN] Failed to write audit log: " + e.getMessage());
        }
    }

    public Optional<User> authenticate(String enteredPin, String requestedRole, String ipAddress) {
        if (enteredPin == null || enteredPin.trim().isEmpty()) {
            return Optional.empty();
        }
        enteredPin = enteredPin.trim();

        User matchedUser = null;

        // 1. If role is explicitly requested, STRICTLY verify PIN for that role ONLY
        if (requestedRole != null && !requestedRole.trim().isEmpty()) {
            String role = requestedRole.trim().toLowerCase();
            List<User> roleUsers = userRepository.findAll().stream()
                    .filter(u -> Boolean.TRUE.equals(u.getIsActive()) && role.equalsIgnoreCase(u.getRole()))
                    .collect(Collectors.toList());
            for (User u : roleUsers) {
                if (SecurityUtils.verifyPin(enteredPin, u.getPinHash())) {
                    matchedUser = u;
                    break;
                }
            }
            if (matchedUser == null && "admin".equalsIgnoreCase(role) && enteredPin.equals(appPin)) {
                matchedUser = userRepository.findByRoleAndIsActiveTrue("admin").orElse(null);
            }
        } else {
            // No role specified: Match any active user by PIN
            List<User> activeUsers = userRepository.findByIsActiveTrue();
            for (User u : activeUsers) {
                if (SecurityUtils.verifyPin(enteredPin, u.getPinHash())) {
                    matchedUser = u;
                    break;
                }
            }
            if (matchedUser == null && enteredPin.equals(appPin)) {
                matchedUser = userRepository.findByRoleAndIsActiveTrue("admin").orElse(null);
            }
        }

        if (matchedUser != null) {
            recordAuditLog("LOGIN_SUCCESS", "USER", String.valueOf(matchedUser.getId()),
                    "User " + matchedUser.getUsername() + " (" + matchedUser.getRole() + ") logged in",
                    matchedUser.getId(), matchedUser.getUsername(), matchedUser.getRole(), ipAddress);
        } else {
            recordAuditLog("LOGIN_FAILED", "USER", null,
                    "Failed login attempt (role requested: " + (requestedRole != null ? requestedRole : "any") + ")",
                    null, "System", "guest", ipAddress);
        }

        return Optional.ofNullable(matchedUser);
    }

    public List<Map<String, Object>> getAllUsers() {
        return userRepository.findAllByOrderByRoleAscIdAsc()
                .stream().map(User::toMap).collect(Collectors.toList());
    }

    @Transactional
    public Map<String, Object> saveUser(Map<String, Object> data, Long currentUserId, String currentUsername, String currentRole, String ipAddress) {
        Map<String, Object> response = new HashMap<>();
        Long id = data.get("id") != null ? Long.valueOf(String.valueOf(data.get("id"))) : null;
        String username = String.valueOf(data.getOrDefault("username", "")).trim().toLowerCase();
        String role = String.valueOf(data.getOrDefault("role", "waiter")).trim().toLowerCase();
        String name = String.valueOf(data.getOrDefault("name", "Staff")).trim();
        String pin = data.get("pin") != null ? String.valueOf(data.get("pin")).trim() : "";
        Boolean isActive = data.get("is_active") != null ? Boolean.valueOf(String.valueOf(data.get("is_active"))) : true;

        if (!List.of("admin", "cashier", "waiter").contains(role)) {
            response.put("success", false);
            response.put("error", "Invalid role. Must be 'admin', 'cashier', or 'waiter'.");
            return response;
        }

        if (id != null) {
            Optional<User> existingOpt = userRepository.findById(id);
            if (existingOpt.isEmpty()) {
                response.put("success", false);
                response.put("error", "User not found");
                return response;
            }
            User user = existingOpt.get();
            if (!pin.isEmpty()) {
                if (pin.length() < 4 || !pin.matches("\\d+")) {
                    response.put("success", false);
                    response.put("error", "PIN must be at least 4 digits long and numeric.");
                    return response;
                }
                user.setPinHash(SecurityUtils.hashPin(pin));
            }
            user.setName(name);
            user.setRole(role);
            user.setIsActive(isActive);
            userRepository.save(user);

            recordAuditLog("USER_UPDATE", "USER", String.valueOf(user.getId()),
                    "Admin updated user " + user.getUsername() + " (Role: " + role + ", Active: " + isActive + ")",
                    currentUserId, currentUsername, currentRole, ipAddress);

            response.put("success", true);
            response.put("message", "User '" + user.getUsername() + "' updated successfully!");
            response.put("user", user.toMap());
        } else {
            if (username.isEmpty()) {
                response.put("success", false);
                response.put("error", "Username is required");
                return response;
            }
            if (pin.isEmpty() || pin.length() < 4 || !pin.matches("\\d+")) {
                response.put("success", false);
                response.put("error", "Initial PIN must be at least 4 digits long and numeric.");
                return response;
            }
            if (userRepository.findByUsername(username).isPresent()) {
                response.put("success", false);
                response.put("error", "Username '" + username + "' already exists");
                return response;
            }

            User newUser = new User(username, role, SecurityUtils.hashPin(pin), name);
            newUser.setIsActive(isActive);
            userRepository.save(newUser);

            recordAuditLog("USER_CREATE", "USER", String.valueOf(newUser.getId()),
                    "Admin created user " + newUser.getUsername() + " (Role: " + role + ")",
                    currentUserId, currentUsername, currentRole, ipAddress);

            response.put("success", true);
            response.put("message", "Staff user '" + username + "' (" + role + ") created successfully!");
            response.put("user", newUser.toMap());
        }

        return response;
    }
}
