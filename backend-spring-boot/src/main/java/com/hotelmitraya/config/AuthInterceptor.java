package com.hotelmitraya.config;

import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import org.springframework.stereotype.Component;
import org.springframework.web.servlet.HandlerInterceptor;

import java.util.List;

@Component
public class AuthInterceptor implements HandlerInterceptor {

    private static final List<String> PUBLIC_PATHS = List.of(
            "/login", "/api/login", "/api/pos/login", "/api/auth/login",
            "/logout", "/api/logout", "/api/auth/logout", "/api/pos/logout",
            "/api/health", "/favicon.ico", "/kitchen", "/kds", "/display", "/bulk",
            "/api/orders/kitchen", "/api/bills", "/api/bills/generate", "/api/next-bill-no"
    );

    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        String path = request.getRequestURI();

        // Allow static resources
        if (path.startsWith("/static/") || path.startsWith("/css/") || path.startsWith("/js/") ||
                path.startsWith("/fonts/") || path.startsWith("/images/") || path.endsWith(".png") ||
                path.endsWith(".css") || path.endsWith(".js") || path.endsWith(".ico")) {
            return true;
        }

        // Allow public API and pages
        for (String p : PUBLIC_PATHS) {
            if (path.equals(p) || path.startsWith(p + "/")) {
                return true;
            }
        }

        HttpSession session = request.getSession(false);
        boolean authenticated = session != null && Boolean.TRUE.equals(session.getAttribute("authenticated"));

        if (!authenticated) {
            if (path.startsWith("/api/")) {
                // For Android API requests passing headers or direct calls, allow if not restricted
                return true;
            }
            response.sendRedirect("/login");
            return false;
        }

        String role = session != null && session.getAttribute("role") != null ?
                String.valueOf(session.getAttribute("role")) : "admin";

        // Role Restrictions
        if ("waiter".equalsIgnoreCase(role)) {
            if (path.startsWith("/admin") || path.startsWith("/api/admin") ||
                path.startsWith("/pos") || path.startsWith("/api/pos") ||
                path.startsWith("/display") || path.startsWith("/printer")) {
                if (path.startsWith("/api/")) {
                    response.setStatus(HttpServletResponse.SC_FORBIDDEN);
                    response.setContentType("application/json");
                    response.getWriter().write("{\"success\":false,\"error\":\"Access denied. Waiter account is not authorized.\",\"forbidden\":true}");
                    return false;
                }
                response.sendRedirect("/waiter");
                return false;
            }
        } else if ("cashier".equalsIgnoreCase(role)) {
            if (path.startsWith("/admin") || path.startsWith("/api/admin")) {
                if (path.startsWith("/api/")) {
                    response.setStatus(HttpServletResponse.SC_FORBIDDEN);
                    response.setContentType("application/json");
                    response.getWriter().write("{\"success\":false,\"error\":\"Access denied. Admin privileges required.\",\"forbidden\":true}");
                    return false;
                }
                response.sendRedirect("/pos");
                return false;
            }
        }

        return true;
    }
}
