import { NextResponse } from 'next/server';

/**
 * Health Check Endpoint
 * Returns system status for monitoring and load balancer health checks
 */

interface HealthStatus {
  status: 'healthy' | 'degraded' | 'unhealthy';
  timestamp: string;
  version: string;
  uptime: number;
  checks: {
    api: boolean;
    memory: boolean;
  };
}

// Track startup time for uptime calculation
const startupTime = Date.now();

export async function GET(): Promise<NextResponse<HealthStatus>> {
  const now = Date.now();
  const uptime = Math.floor((now - startupTime) / 1000);
  
  // Basic memory check (under 1GB used)
  const memoryUsage = process.memoryUsage();
  const memoryOk = memoryUsage.heapUsed < 1024 * 1024 * 1024;
  
  const allChecksPass = memoryOk;
  
  const health: HealthStatus = {
    status: allChecksPass ? 'healthy' : 'degraded',
    timestamp: new Date().toISOString(),
    version: '3.0.0',
    uptime,
    checks: {
      api: true,
      memory: memoryOk,
    },
  };
  
  return NextResponse.json(health, {
    status: allChecksPass ? 200 : 503,
    headers: {
      'Cache-Control': 'no-store, no-cache, must-revalidate',
    },
  });
}
