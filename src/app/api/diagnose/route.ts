import { NextRequest, NextResponse } from 'next/server';
import { spawn } from 'child_process';
import { existsSync } from 'fs';
import path from 'path';

// Helper to parse Python errors into user-friendly messages
function parsePythonError(stderr: string, exitCode: number | null): { message: string; details: string; hint: string } {
  const stderrLower = stderr.toLowerCase();
  
  // Check for missing module errors
  const moduleMatch = stderr.match(/ModuleNotFoundError: No module named '([^']+)'/);
  if (moduleMatch) {
    const moduleName = moduleMatch[1];
    return {
      message: `Python dependency missing: ${moduleName}`,
      details: stderr,
      hint: `Run: source .venv/bin/activate && pip install -r requirements.txt`
    };
  }
  
  // Check for import errors (often means partially installed deps)
  if (stderrLower.includes('importerror')) {
    return {
      message: 'Python import error - dependencies may be corrupted',
      details: stderr,
      hint: 'Try: source .venv/bin/activate && pip install --force-reinstall -r requirements.txt'
    };
  }
  
  // Check for syntax errors in Python code
  if (stderrLower.includes('syntaxerror')) {
    return {
      message: 'Python syntax error in logic modules',
      details: stderr,
      hint: 'Check the Python files in the logic/ directory for syntax errors'
    };
  }
  
  // Check for API/network errors (e.g., OpenAI)
  if (stderrLower.includes('openai') || stderrLower.includes('api')) {
    return {
      message: 'External API error',
      details: stderr,
      hint: 'Check your API keys in .env and network connectivity'
    };
  }
  
  // Generic Python error
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
          details: `Expected Python at: ${pythonPath}`,
          hint: 'Run: python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt'
        },
        { status: 500 }
      );
    }
    
    const body = await request.json();
    
    // Run the Python script with the request body as input
    const result = await new Promise<string>((resolve, reject) => {
      const python = spawn(pythonPath, ['-c', `
import sys
import json
sys.path.insert(0, '${projectRoot}')

from logic.config_loader import ConfigLoader
from logic.dns_lookup import DNSLookup
from logic.email_detector import EmailDetector
from logic.decision_engine import DecisionEngine
from logic.action_plan_builder import ActionPlanBuilder
from logic.ai_translator import AITranslator

data = json.loads('''${JSON.stringify(body)}''')

domain = data.get('domain')
platform = data.get('platform', 'attractwell')
sections = data.get('sections', ['all'])
intent_input = data.get('intent', {})
ai_audience = data.get('ai_audience', 'customer')
use_ai = data.get('use_ai', True)

if not domain:
    print(json.dumps({"error": "Domain is required"}))
    sys.exit(0)

# 1. Load Config
config = ConfigLoader()

# 2. DNS Lookup
dns_tool = DNSLookup()
snapshot = dns_tool.get_all_records(domain, filter_sections=sections)

# 3. Email Detection
email_tool = EmailDetector(config.get_email_rules())
mx_records = snapshot.get('MX', [])
txt_records = snapshot.get('TXT', [])

email_state = email_tool.detect_provider(mx_records)
email_state.update(email_tool.analyze_txt_records(txt_records))
email_state.update(email_tool.analyze_dns_snapshot(snapshot))

dkim_records = snapshot.get('DKIM', [])
email_state.update(email_tool.analyze_dkim(dkim_records))

# 4. Decision Engine
decision_engine = DecisionEngine(config)

intent = {
    "has_external_dependencies": intent_input.get('has_external_dependencies', False),
    "email_managed_by_platform": intent_input.get('email_managed_by_platform', False),
    "comfortable_editing_dns": intent_input.get('comfortable_editing_dns', True),
    "registrar_known": intent_input.get('registrar_known', True),
    "delegate_dns_management": intent_input.get('delegate_dns_management', False),
    "queried_sections": sections
}

decision = decision_engine.evaluate(domain, platform, intent, email_state, snapshot)

# 5. Action Plan
builder = ActionPlanBuilder(config)
final_plan = builder.build_plan(decision, snapshot, email_state)

# 6. AI Translation
if use_ai:
    try:
        translator = AITranslator()
        if ai_audience == 'both':
            ai_insights = translator.translate_both(final_plan)
        else:
            ai_insights = translator.translate_diagnostic(final_plan, audience=ai_audience)
        final_plan["ai_insights"] = ai_insights
    except Exception as ai_error:
        final_plan["ai_insights"] = {"error": str(ai_error)}
else:
    final_plan["ai_insights"] = None

print(json.dumps(final_plan))
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
          // Create a structured error with stderr and exit code
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
    console.error('[API] Diagnose error:', error);
    
    // Check if this is a Python execution error with stderr
    if (error.stderr !== undefined) {
      const parsedError = parsePythonError(error.stderr, error.exitCode);
      console.error('[API] Parsed Python error:', parsedError);
      return NextResponse.json(
        {
          error: parsedError.message,
          details: parsedError.details,
          hint: parsedError.hint
        },
        { status: 500 }
      );
    }
    
    // Check for JSON parsing errors (Python returned invalid output)
    if (error instanceof SyntaxError && error.message.includes('JSON')) {
      return NextResponse.json(
        {
          error: 'Python script returned invalid JSON',
          details: error.message,
          hint: 'Check the Python logic modules for errors in JSON output'
        },
        { status: 500 }
      );
    }
    
    // Check for spawn errors (Python executable issues)
    if (error.code === 'ENOENT') {
      return NextResponse.json(
        {
          error: 'Python executable not found',
          details: `Could not find Python at: ${pythonPath}`,
          hint: 'Ensure the virtual environment is set up: python3 -m venv .venv'
        },
        { status: 500 }
      );
    }
    
    // Generic error fallback
    return NextResponse.json(
      {
        error: error.message || 'Internal server error',
        details: error.stack || 'No stack trace available',
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
