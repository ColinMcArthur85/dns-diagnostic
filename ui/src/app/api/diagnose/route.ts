import { NextRequest, NextResponse } from 'next/server';
import { execFile } from 'child_process';
import path from 'path';
import { promisify } from 'util';
import { checkRateLimit, getClientIP, createRateLimitHeaders } from '@/lib/rate-limiter';

const execFilePromise = promisify(execFile);

// Input validation regex for domain names (RFC 1035 compliant)
const DOMAIN_REGEX = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;
const MAX_DOMAIN_LENGTH = 253;

// Blocked domain patterns (SSRF protection)
const BLOCKED_PATTERNS = [
  /\.local$/i,
  /\.internal$/i,
  /\.corp$/i,
  /\.intranet$/i,
  /^localhost$/i,
  /^127\./,
  /^10\./,
  /^192\.168\./,
  /^172\.(1[6-9]|2[0-9]|3[0-1])\./,
];

// Whitelist for platforms
const VALID_PLATFORMS = ['attractwell', 'aw', 'getoiling', 'go'];
const VALID_AUDIENCES = ['customer', 'support', 'both'];
const VALID_SECTIONS = ['all', 'web', 'email', 'A', 'CNAME', 'MX', 'TXT', 'SPF', 'DMARC', 'DKIM', 'NS'];

function isValidDomain(domain: string): boolean {
  if (!domain || typeof domain !== 'string') return false;
  if (domain.length > MAX_DOMAIN_LENGTH) return false;
  if (!DOMAIN_REGEX.test(domain)) return false;
  
  // Block internal/private domains (SSRF protection)
  for (const pattern of BLOCKED_PATTERNS) {
    if (pattern.test(domain)) return false;
  }
  
  return true;
}

function sanitizeSections(sections: unknown): string[] {
  if (!sections || !Array.isArray(sections)) return [];
  return sections.filter((s): s is string => typeof s === 'string' && VALID_SECTIONS.includes(s));
}

interface DiagnoseIntent {
  has_external_dependencies?: boolean;
  email_managed_by_platform?: boolean;
  email_provided_by_platform?: boolean;
  comfortable_editing_dns?: boolean;
  registrar_known?: boolean;
  delegate_dns_management?: boolean;
  email_choice?: string;
}

export async function POST(req: NextRequest) {
  try {
    // === RATE LIMITING (P2-10) ===
    const clientIP = getClientIP(req.headers);
    const rateLimitResult = checkRateLimit(clientIP, 'diagnose');
    
    if (!rateLimitResult.allowed) {
      return NextResponse.json(
        { 
          error: 'Rate limit exceeded', 
          hint: `Please wait ${rateLimitResult.retryAfter} seconds before trying again`,
          code: 'RATE_LIMITED'
        },
        { 
          status: 429,
          headers: createRateLimitHeaders(rateLimitResult)
        }
      );
    }

    const body = await req.json();
    const { domain, platform, intent, sections, ai_audience } = body as {
      domain: string;
      platform: string;
      intent?: DiagnoseIntent;
      sections?: unknown;
      ai_audience?: string;
    };

    // === INPUT VALIDATION ===
    
    // 1. Validate domain (CRITICAL - prevents command injection)
    if (!isValidDomain(domain)) {
      return NextResponse.json({ 
        error: 'Invalid domain format',
        hint: 'Domain must be a valid hostname (e.g., example.com)'
      }, { status: 400 });
    }

    // 2. Validate platform
    if (!platform || !VALID_PLATFORMS.includes(platform)) {
      return NextResponse.json({ 
        error: 'Invalid platform',
        hint: 'Platform must be one of: attractwell, aw, getoiling, go'
      }, { status: 400 });
    }

    // 3. Validate AI audience
    const validatedAudience = VALID_AUDIENCES.includes(ai_audience || '') ? ai_audience! : 'customer';

    // 4. Validate sections
    const validatedSections = sanitizeSections(sections);

    // === BUILD COMMAND SAFELY WITH execFile() ===
    // Using execFile() with array arguments prevents shell injection
    const pythonPath = 'python3';
    const scriptPath = path.join(process.cwd(), '..', 'src', 'main.py');
    
    const args = [
      scriptPath,
      '--domain', domain,  // Already validated above
      '--platform', platform,  // Already validated above
      '--ai',
      '--ai-audience', validatedAudience
    ];

    // Add validated sections
    if (validatedSections.length > 0 && !validatedSections.includes('all')) {
      args.push('--sections', ...validatedSections);
    }

    // Add intent flags (booleans only - safe)
    if (intent?.has_external_dependencies === true) args.push('--has-external');
    if (intent?.email_managed_by_platform === true) args.push('--email-managed');
    if (intent?.email_provided_by_platform === true) args.push('--email-provided-by-platform');
    if (intent?.comfortable_editing_dns === true) args.push('--comfortable');
    if (intent?.registrar_known === true) args.push('--registrar-known');
    if (intent?.delegate_dns_management === true) args.push('--delegate-dns');
    
    // Email choice validation
    if (intent?.email_choice && ['aw', 'go', 'external', 'none'].includes(intent.email_choice)) {
      args.push('--email-choice', intent.email_choice);
    }

    // === EXECUTE SAFELY ===
    try {
      const { stdout, stderr } = await execFilePromise(pythonPath, args, {
        timeout: 60000, // 60 second timeout
        maxBuffer: 2 * 1024 * 1024, // 2MB buffer limit
      });

      if (stderr && !stdout) {
        const isDev = process.env.NODE_ENV === 'development';
        return NextResponse.json({ 
          error: isDev ? stderr : 'Diagnosis failed',
          code: 'DIAGNOSIS_ERROR'
        }, { status: 500 });
      }

      const result = JSON.parse(stdout);
      return NextResponse.json(result);

    } catch (execError: unknown) {
      const isDev = process.env.NODE_ENV === 'development';
      const errorMessage = execError instanceof Error ? execError.message : 'Execution failed';
      return NextResponse.json({ 
        error: isDev ? errorMessage : 'Diagnosis failed',
        code: 'EXEC_ERROR'
      }, { status: 500 });
    }

  } catch (error: unknown) {
    const isDev = process.env.NODE_ENV === 'development';
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('Diagnosis error:', error);
    return NextResponse.json({ 
      error: isDev ? errorMessage : 'An internal error occurred',
      code: 'INTERNAL_ERROR'
    }, { status: 500 });
  }
}
