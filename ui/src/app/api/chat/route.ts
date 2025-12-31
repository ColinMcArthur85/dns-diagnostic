import { NextRequest, NextResponse } from 'next/server';
import { execFile } from 'child_process';
import path from 'path';
import { promisify } from 'util';
import crypto from 'crypto';
import { checkRateLimit, getClientIP, createRateLimitHeaders } from '@/lib/rate-limiter';

const execFilePromise = promisify(execFile);

// === SESSION MANAGEMENT WITH LIMITS ===
interface Session {
  diagnostic_data: Record<string, unknown>;
  history: Array<{ role: string; content: string }>;
  audience: string;
  created_at: number;
  last_accessed: number;
}

const MAX_SESSIONS = 1000;
const SESSION_TTL_MS = 15 * 60 * 1000; // 15 minutes
const MAX_HISTORY_LENGTH = 50;  // Max conversation turns
const MAX_MESSAGE_LENGTH = 2000;  // Max chars per message

const conversations = new Map<string, Session>();

// Cleanup expired sessions periodically
function cleanupSessions(): void {
  const now = Date.now();
  for (const [id, session] of conversations.entries()) {
    if (now - session.last_accessed > SESSION_TTL_MS) {
      conversations.delete(id);
    }
  }
  
  // If still over limit, remove oldest
  if (conversations.size > MAX_SESSIONS) {
    const sorted = Array.from(conversations.entries())
      .sort((a, b) => a[1].last_accessed - b[1].last_accessed);
    
    const toRemove = sorted.slice(0, sorted.length - MAX_SESSIONS);
    for (const [id] of toRemove) {
      conversations.delete(id);
    }
  }
}

// Run cleanup every 5 minutes
if (typeof setInterval !== 'undefined') {
  setInterval(cleanupSessions, 5 * 60 * 1000);
}

// === INPUT VALIDATION ===
const VALID_AUDIENCES = ['customer', 'support'];
const VALID_ACTIONS = ['start', 'chat'];

function isValidAudience(audience: unknown): audience is string {
  return typeof audience === 'string' && VALID_AUDIENCES.includes(audience);
}

function sanitizeMessage(message: unknown): string {
  if (typeof message !== 'string') return '';
  // Truncate and remove control characters
  return message.slice(0, MAX_MESSAGE_LENGTH).replace(/[\x00-\x1f\x7f]/g, '');
}

function generateSessionId(): string {
  return crypto.randomBytes(16).toString('hex');
}

export async function POST(req: NextRequest) {
  try {
    // === RATE LIMITING (P2-10) ===
    const clientIP = getClientIP(req.headers);
    const rateLimitResult = checkRateLimit(clientIP, 'chat');
    
    if (!rateLimitResult.allowed) {
      return NextResponse.json(
        { 
          error: 'Rate limit exceeded', 
          hint: `Please wait ${rateLimitResult.retryAfter} seconds`,
          code: 'RATE_LIMITED'
        },
        { 
          status: 429,
          headers: createRateLimitHeaders(rateLimitResult)
        }
      );
    }

    const body = await req.json();
    const { session_id, message, diagnostic_data, audience = 'customer', action } = body as {
      session_id?: string;
      message?: unknown;
      diagnostic_data?: Record<string, unknown>;
      audience?: unknown;
      action?: string;
    };

    // Validate action
    if (!action || !VALID_ACTIONS.includes(action)) {
      return NextResponse.json({ error: 'Invalid action' }, { status: 400 });
    }

    const pythonPath = 'python3';
    const scriptPath = path.join(process.cwd(), '..', 'src', 'conversational_cli.py');

    // === START NEW CONVERSATION ===
    if (action === 'start') {
      // Cleanup before creating new session
      cleanupSessions();
      
      // Validate diagnostic data exists
      if (!diagnostic_data || typeof diagnostic_data !== 'object') {
        return NextResponse.json({ error: 'Invalid diagnostic data' }, { status: 400 });
      }

      const validatedAudience = isValidAudience(audience) ? audience : 'customer';
      const newSessionId = generateSessionId();

      const args = [
        scriptPath,
        'start',
        '--diagnostic', JSON.stringify(diagnostic_data),
        '--audience', validatedAudience
      ];

      try {
        const { stdout, stderr } = await execFilePromise(pythonPath, args, {
          timeout: 30000,
          maxBuffer: 1024 * 1024,
        });

        if (stderr && !stdout) {
          const isDev = process.env.NODE_ENV === 'development';
          return NextResponse.json({ 
            error: isDev ? stderr : 'Failed to start conversation',
            code: 'START_ERROR'
          }, { status: 500 });
        }

        const result = JSON.parse(stdout);
        
        // Store session with the new ID
        conversations.set(newSessionId, {
          diagnostic_data,
          history: [],
          audience: validatedAudience,
          created_at: Date.now(),
          last_accessed: Date.now()
        });
        
        // Override session_id with our secure one
        result.session_id = newSessionId;
        return NextResponse.json(result);

      } catch (execError: unknown) {
        const isDev = process.env.NODE_ENV === 'development';
        const errorMessage = execError instanceof Error ? execError.message : 'Execution failed';
        return NextResponse.json({ 
          error: isDev ? errorMessage : 'Failed to start conversation',
          code: 'EXEC_ERROR'
        }, { status: 500 });
      }
    }

    // === CONTINUE CONVERSATION ===
    if (action === 'chat') {
      // Validate session
      if (!session_id || typeof session_id !== 'string') {
        return NextResponse.json({ error: 'Session ID required' }, { status: 400 });
      }

      if (!conversations.has(session_id)) {
        return NextResponse.json({ 
          error: 'Invalid or expired session',
          hint: 'Please start a new conversation'
        }, { status: 400 });
      }

      const session = conversations.get(session_id)!;
      
      // Check session expiration
      if (Date.now() - session.last_accessed > SESSION_TTL_MS) {
        conversations.delete(session_id);
        return NextResponse.json({ 
          error: 'Session expired',
          hint: 'Please start a new conversation'
        }, { status: 400 });
      }

      // Validate and sanitize message
      const sanitizedMessage = sanitizeMessage(message);
      if (!sanitizedMessage) {
        return NextResponse.json({ error: 'Message required' }, { status: 400 });
      }

      // Limit history size
      const trimmedHistory = session.history.slice(-MAX_HISTORY_LENGTH);

      const args = [
        scriptPath,
        'chat',
        '--diagnostic', JSON.stringify(session.diagnostic_data),
        '--history', JSON.stringify(trimmedHistory),
        '--message', sanitizedMessage,
        '--audience', session.audience
      ];

      try {
        const { stdout, stderr } = await execFilePromise(pythonPath, args, {
          timeout: 30000,
          maxBuffer: 1024 * 1024,
        });

        if (stderr && !stdout) {
          const isDev = process.env.NODE_ENV === 'development';
          return NextResponse.json({ 
            error: isDev ? stderr : 'Failed to process message',
            code: 'CHAT_ERROR'
          }, { status: 500 });
        }

        const result = JSON.parse(stdout);
        
        // Update session
        session.history.push({ role: 'user', content: sanitizedMessage });
        session.history.push({ role: 'assistant', content: result.message || '' });
        session.last_accessed = Date.now();
        
        return NextResponse.json(result);

      } catch (execError: unknown) {
        const isDev = process.env.NODE_ENV === 'development';
        const errorMessage = execError instanceof Error ? execError.message : 'Execution failed';
        return NextResponse.json({ 
          error: isDev ? errorMessage : 'Failed to process message',
          code: 'EXEC_ERROR'
        }, { status: 500 });
      }
    }

    return NextResponse.json({ error: 'Invalid action' }, { status: 400 });

  } catch (error: unknown) {
    const isDev = process.env.NODE_ENV === 'development';
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('Conversation error:', error);
    return NextResponse.json({ 
      error: isDev ? errorMessage : 'An internal error occurred',
      code: 'INTERNAL_ERROR'
    }, { status: 500 });
  }
}
