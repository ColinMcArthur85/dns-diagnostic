import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';

/**
 * Trace API - Compare cached vs authoritative DNS records
 * 
 * This endpoint bypasses DNS cache to query authoritative nameservers directly.
 * Useful for verifying recent DNS changes before full propagation.
 */

// Helper to parse Python errors (shared with diagnose route)
function parsePythonError(stderr: string, exitCode: number | null): { message: string; details: string; hint: string } {
  const stderrLower = stderr.toLowerCase();
  
  const moduleMatch = stderr.match(/ModuleNotFoundError: No module named '([^']+)'/);
  if (moduleMatch) {
    return {
      message: `Python dependency missing: ${moduleMatch[1]}`,
      details: stderr,
      hint: 'Run: source .venv/bin/activate && pip install -r requirements.txt'
    };
  }
  
  if (stderrLower.includes('syntaxerror')) {
    return {
      message: 'Python syntax error in logic modules',
      details: stderr,
      hint: 'Check the Python files in the logic/ directory for syntax errors'
    };
  }
  
  return {
    message: `Python process failed with exit code ${exitCode}`,
    details: stderr || 'No error output captured',
    hint: 'Check the server logs for more details'
  };
}

export async function POST(request: NextRequest) {
  const projectRoot = process.cwd();
  const pythonPath = path.join(projectRoot, '.venv', 'bin', 'python3');
  
  try {
    // Pre-flight check: Verify virtual environment exists
    if (!existsSync(pythonPath)) {
      console.error(`[API] Python venv not found at: ${pythonPath}`);
      return NextResponse.json(
        {
          error: 'Python virtual environment not found',
          hint: 'Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt'
        },
        { status: 500 }
      );
    }
    
    const body = await request.json();
    const { domain, record_type } = body;
    
    // Validate required fields
    if (!domain) {
      return NextResponse.json(
        { error: 'Domain is required' },
        { status: 400 }
      );
    }
    
    if (!record_type) {
      return NextResponse.json(
        { error: 'Record type is required (e.g., A, CNAME, MX, TXT)' },
        { status: 400 }
      );
    }
    
    // Valid record types
    const validTypes = ['A', 'AAAA', 'CNAME', 'MX', 'TXT', 'NS'];
    if (!validTypes.includes(record_type.toUpperCase())) {
      return NextResponse.json(
        { error: `Invalid record type. Must be one of: ${validTypes.join(', ')}` },
        { status: 400 }
      );
    }
    
    // Run the Python trace
    const result = await new Promise<string>((resolve, reject) => {
      const python = spawn(pythonPath, ['-c', `
import sys
import json
sys.path.insert(0, '${projectRoot}')

from logic.dns_lookup import DNSLookup

domain = '''${domain}'''
record_type = '''${record_type.toUpperCase()}'''

dns = DNSLookup()
result = dns.trace_record(domain, record_type)

print(json.dumps(result))
      `]);

      let stdout = '';
      let stderr = '';

      python.stdout.on('data', (data) => {
        stdout += data.toString();
      });

      python.stderr.on('data', (data) => {
        stderr += data.toString();
      });

      python.on('close', (code) => {
        if (code !== 0) {
          const error = new Error(stderr || `Python process exited with code ${code}`) as Error & { stderr: string; exitCode: number | null };
          error.stderr = stderr;
          error.exitCode = code;
          reject(error);
        } else {
          resolve(stdout);
        }
      });

      python.on('error', (err) => {
        reject(err);
      });
    });

    const jsonResult = JSON.parse(result.trim());
    return NextResponse.json(jsonResult);

  } catch (error: any) {
    console.error('[API] Trace error:', error);
    
    if (error.stderr !== undefined) {
      const parsedError = parsePythonError(error.stderr, error.exitCode);
      return NextResponse.json(
        {
          error: parsedError.message,
          details: parsedError.details,
          hint: parsedError.hint
        },
        { status: 500 }
      );
    }
    
    if (error instanceof SyntaxError && error.message.includes('JSON')) {
      return NextResponse.json(
        {
          error: 'Python script returned invalid JSON',
          hint: 'Check the Python logic modules for errors'
        },
        { status: 500 }
      );
    }
    
    return NextResponse.json(
      {
        error: error.message || 'Internal server error',
        hint: 'Check the server console for more details'
      },
      { status: 500 }
    );
  }
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}
