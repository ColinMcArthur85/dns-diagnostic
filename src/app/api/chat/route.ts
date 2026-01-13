import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';

/**
 * Chat API - Conversational interface for DNS diagnostics
 * 
 * This endpoint provides a conversational interface grounded in diagnostic data.
 * The AI maintains conversation history and can answer follow-up questions.
 */

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
    
    // Run the Python chat script
    const result = await new Promise<string>((resolve, reject) => {
      const python = spawn(pythonPath, ['-c', `
import sys
import json
sys.path.insert(0, '${projectRoot}')

from logic.conversational_agent import ConversationalAgent

data = json.loads('''${JSON.stringify(body)}''')

user_message = data.get('message', '')
diagnostic_data = data.get('diagnostic_data', {})
audience = data.get('audience', 'customer')
conversation_history = data.get('conversation_history', [])

if not user_message:
    print(json.dumps({"error": "Message is required"}))
    sys.exit(0)

if not diagnostic_data:
    print(json.dumps({"error": "diagnostic_data is required. Run a diagnosis first."}))
    sys.exit(0)

try:
    agent = ConversationalAgent()
    
    # Call with correct parameter names matching the method signature
    response = agent.chat(
        diagnostic_data=diagnostic_data,
        conversation_history=conversation_history,
        user_message=user_message,
        audience=audience
    )
    print(json.dumps(response))
except Exception as e:
    print(json.dumps({"error": str(e), "message": "Failed to generate response"}))
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
    console.error('[API] Chat error:', error);
    
    // Check for Python execution errors with stderr
    if (error.stderr !== undefined) {
      // Check for common issues
      if (error.stderr.includes('ModuleNotFoundError')) {
        const moduleMatch = error.stderr.match(/No module named '([^']+)'/);
        return NextResponse.json(
          {
            error: `Python dependency missing: ${moduleMatch?.[1] || 'unknown'}`,
            hint: 'Run: source .venv/bin/activate && pip install -r requirements.txt'
          },
          { status: 500 }
        );
      }
      return NextResponse.json(
        { error: error.message, details: error.stderr },
        { status: 500 }
      );
    }
    
    return NextResponse.json(
      { error: error.message || 'Internal server error' },
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
