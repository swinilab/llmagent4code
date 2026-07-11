package com.chatdev.oms.config;

import org.springframework.web.filter.OncePerRequestFilter;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import java.io.IOException;

/**
 * Graceful degradation filter for NFR 3.1.
 * When degradation mode is enabled, non-essential features are disabled.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DegradationFilter extends OncePerRequestFilter {

    private final AppProperties appProperties;

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {

        String uri = request.getRequestURI();

        // Check if non-essential features are being accessed during degradation
        if (!appProperties.getFeatures().isRecommendationsEnabled() && 
            uri.contains("/recommendations")) {
            log.warn("Recommendations feature disabled - returning 503");
            response.setStatus(HttpServletResponse.SC_SERVICE_UNAVAILABLE);
            response.getWriter().write("{\"error\": \"Feature temporarily unavailable\"}");
            return;
        }

        if (!appProperties.getFeatures().isAnalyticsEnabled() && 
            uri.contains("/analytics")) {
            log.warn("Analytics feature disabled - returning 503");
            response.setStatus(HttpServletResponse.SC_SERVICE_UNAVAILABLE);
            response.getWriter().write("{\"error\": \"Feature temporarily unavailable\"}");
            return;
        }

        filterChain.doFilter(request, response);
    }
}
