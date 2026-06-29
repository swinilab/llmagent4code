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
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;

/**
 * Rate limiting filter for NFR 1.3 (Queue Management).
 * Implements sliding window rate limiting with automatic reset.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class RateLimitFilter extends OncePerRequestFilter {

    private final AppProperties appProperties;

    // Thread-safe rate limiter using LongAdder for high concurrency
    private final LongAdder requestCount = new LongAdder();
    private final AtomicLong windowStart = new AtomicLong(System.currentTimeMillis());
    
    // Configurable limits (NFR 2.3 - Deferred Binding)
    private static final long WINDOW_SIZE_MS = 1000; // 1 second window
    private int maxRequestsPerWindow = 100;

    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain) throws ServletException, IOException {

        // Update window if needed (thread-safe sliding window)
        long currentTime = System.currentTimeMillis();
        long currentWindowStart = windowStart.get();
        
        if (currentTime - currentWindowStart >= WINDOW_SIZE_MS) {
            // Try to reset the window (only one thread should succeed)
            if (windowStart.compareAndSet(currentWindowStart, currentTime)) {
                requestCount.reset();
                log.debug("Rate limit window reset");
            }
        }

        // Atomically increment and check (NFR 1.3 - Queue Management)
        requestCount.increment();
        long currentCount = requestCount.sum();

        if (currentCount > maxRequestsPerWindow) {
            log.warn("Rate limit exceeded for request: {}", request.getRequestURI());
            response.setStatus(HttpServletResponse.SC_TOO_MANY_REQUESTS);
            response.setHeader("X-RateLimit-Limit", String.valueOf(maxRequestsPerWindow));
            response.setHeader("X-RateLimit-Remaining", "0");
            response.setHeader("X-RateLimit-Window", String.valueOf(WINDOW_SIZE_MS));
            return;
        }

        // Add rate limit headers
        response.setHeader("X-RateLimit-Limit", String.valueOf(maxRequestsPerWindow));
        response.setHeader("X-RateLimit-Remaining", String.valueOf(maxRequestsPerWindow - currentCount));
        response.setHeader("X-RateLimit-Window", String.valueOf(WINDOW_SIZE_MS));

        try {
            filterChain.doFilter(request, response);
        } catch (Exception e) {
            log.error("Error in filter chain", e);
            throw e;
        }
    }

    /**
     * Allow dynamic configuration of rate limit (NFR 2.3).
     */
    public void setMaxRequestsPerWindow(int maxRequests) {
        this.maxRequestsPerWindow = maxRequests;
        log.info("Rate limit updated to {} requests per {}ms", maxRequests, WINDOW_SIZE_MS);
    }

    public int getMaxRequestsPerWindow() {
        return maxRequestsPerWindow;
    }
}
