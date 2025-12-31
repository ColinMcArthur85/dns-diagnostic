import { NextRequest, NextResponse } from 'next/server';
import { execFile } from 'child_process';
import path from 'path';
import { promisify } from 'util';

const execFilePromise = promisify(execFile);

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { session_id, message, diagnostic_data, audience, action } = body;

    const pythonScript = path.join(process.cwd(), 'logic', 'conversational_cli.py');
    const args = ['--audience', audience || 'customer'];

    if (action === 'start') {
      args.push('--start');
    } else {
      args.push('--session-id', session_id);
      args.push('--message', message);
    }

    // Pass diagnostic data as JSON string argument
    args.push('--data', JSON.stringify(diagnostic_data));

    const { stdout, stderr } = await execFilePromise('python3', [pythonScript, ...args], {
      env: { ...process.env, PYTHONPATH: process.cwd() }
    });

    if (stderr && !stdout) {
      return NextResponse.json({ error: stderr }, { status: 500 });
    }

    return NextResponse.json(JSON.parse(stdout));

  } catch (error: any) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
