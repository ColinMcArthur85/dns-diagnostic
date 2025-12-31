/**
 * Rate Limiter Middleware
 * Implements P2-10: Rate limiting to prevent abuse
 * 
 * This is a simple in-memory rate limiter suitable for single-server deployments.
 * For production with multiple servers, use Redis-based rate limiting.
 */

interface RateLimitEntry {
  count: number;
  resetTime: number;
}

// In-memory store for rate limiting
const rateLimitStore = new Map<string, RateLimitEntry>();

// Configuration
const RATE_LIMIT_CONFIG = {
  // Diagnostic endpoint: 10 requests per minute
  diagnose: {
    maxRequests: 10,
    windowMs: 60 * 1000,  // 1 minute
  },
  // Chat endpoint: 30 requests per minute (more conversational)
  chat: {
    maxRequests: 30,
    windowMs: 60 * 1000,  // 1 minute
  },
  // Default: 20 requests per minute
  default: {
    maxRequests: 20,
    windowMs: 60 * 1000,
  },
};

// Cleanup old entries every 5 minutes
const CLEANUP_INTERVAL = 5 * 60 * 1000;

function cleanup(): void {
  const now = Date.now();
  for (const [key, entry] of rateLimitStore.entries()) {
    if (now > entry.resetTime) {
      rateLimitStore.delete(key);
    }
  }
}

// Run cleanup periodically
if (typeof setInterval !== 'undefined') {
  setInterval(cleanup, CLEANUP_INTERVAL);
}

export interface RateLimitResult {
  allowed: boolean;
  remaining: number;
  resetTime: number;
  retryAfter?: number;
}

/**
 * Check if request is allowed under rate limit
 * 
 * @param identifier - Unique identifier (IP address or user ID)
 * @param endpoint - Endpoint type ('diagnose', 'chat', or 'default')
 * @returns Rate limit check result
 */
export function checkRateLimit(
  identifier: string,
  endpoint: 'diagnose' | 'chat' | 'default' = 'default'
): RateLimitResult {
  const config = RATE_LIMIT_CONFIG[endpoint];
  const key = `${endpoint}:${identifier}`;
  const now = Date.now();
  
  let entry = rateLimitStore.get(key);
  
  // If no entry or window expired, create new entry
  if (!entry || now > entry.resetTime) {
    entry = {
      count: 0,
      resetTime: now + config.windowMs,
    };
    rateLimitStore.set(key, entry);
  }
  
  // Check if limit exceeded
  if (entry.count >= config.maxRequests) {
    const retryAfter = Math.ceil((entry.resetTime - now) / 1000);
    return {
      allowed: false,
      remaining: 0,
      resetTime: entry.resetTime,
      retryAfter,
    };
  }
  
  // Increment counter
  entry.count += 1;
  
  return {
    allowed: true,
    remaining: config.maxRequests - entry.count,
    resetTime: entry.resetTime,
  };
}

/**
 * Get client IP from request headers
 * Handles proxied requests (X-Forwarded-For, etc.)
 */
export function getClientIP(headers: Headers): string {
  // Check common proxy headers
  const forwardedFor = headers.get('x-forwarded-for');
  if (forwardedFor) {
    // Get first IP if comma-separated list
    return forwardedFor.split(',')[0].trim();
  }
  
  const realIP = headers.get('x-real-ip');
  if (realIP) {
    return realIP.trim();
  }
  
  // Fallback (not ideal, but better than nothing)
  return 'unknown';
}

/**
 * Create rate limit headers for response
 */
export function createRateLimitHeaders(result: RateLimitResult): Record<string, string> {
  const headers: Record<string, string> = {
    'X-RateLimit-Remaining': result.remaining.toString(),
    'X-RateLimit-Reset': Math.ceil(result.resetTime / 1000).toString(),
  };
  
  if (!result.allowed && result.retryAfter) {
    headers['Retry-After'] = result.retryAfter.toString();
  }
  
  return headers;
}
