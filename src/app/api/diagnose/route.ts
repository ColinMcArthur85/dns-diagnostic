import { NextRequest, NextResponse } from 'next/server';
import { execFile } from 'child_process';
import path from 'path';
import { promisify } from 'util';

const execFilePromise = promisify(execFile);

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const { domain, platform, intent, sections, ai_audience } = body;

    if (!domain) {
      return NextResponse.json({ error: 'Domain is required' }, { status: 400 });
    }

    // Build arguments for python script
    const pythonScript = path.join(process.cwd(), 'logic', 'main.py');
    const args = [
      '--domain', domain,
      '--platform', platform || 'attractwell'
    ];

    if (intent?.has_external_dependencies) args.push('--has-external');
    if (intent?.email_managed_by_platform) args.push('--email-managed');
    if (intent?.comfortable_editing_dns) args.push('--comfortable');
    if (intent?.registrar_known) args.push('--registrar-known');
    if (intent?.delegate_dns_management) args.push('--delegate-dns');
    
    if (sections && Array.isArray(sections) && !sections.includes('all')) {
      args.push('--sections', ...sections);
    }

    // AI Translation
    args.push('--ai');
    args.push('--ai-audience', ai_audience || 'customer');

    const { stdout, stderr } = await execFilePromise('python3', [pythonScript, ...args], {
      env: { ...process.env, PYTHONPATH: process.cwd() }
    });

    if (stderr && !stdout) {
      console.error('Python Error:', stderr);
      return NextResponse.json({ error: stderr }, { status: 500 });
    }

    return NextResponse.json(JSON.parse(stdout));

  } catch (error: any) {
    console.error('API Error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
