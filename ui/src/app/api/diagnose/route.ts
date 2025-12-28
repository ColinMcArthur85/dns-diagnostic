import { NextRequest, NextResponse } from 'next/server';
import { exec } from 'child_process';
import path from 'path';
import { promisify } from 'util';

const execPromise = promisify(exec);

export async function POST(req: NextRequest) {
  try {
    const { domain, platform, intent, sections } = await req.json();

    // Construct the command
    // We navigate up to the root from the 'ui' folder to find 'src/main.py'
    const pythonPath = 'python3'; // Adjust if needed
    const scriptPath = path.join(process.cwd(), '..', 'src', 'main.py');
    
    let command = `${pythonPath} ${scriptPath} --domain ${domain} --platform ${platform} --ai`;
    
    // Add sections if specified and not 'all'
    if (sections && Array.isArray(sections) && sections.length > 0 && !sections.includes('all')) {
      command += ` --sections ${sections.join(' ')}`;
    }

    // Add intent flags
    if (intent?.has_external_dependencies) command += ' --has-external';
    if (intent?.email_managed_by_platform) command += ' --email-managed';
    if (intent?.email_provided_by_platform) command += ' --email-provided-by-platform';
    if (intent?.email_choice) command += ` --email-choice ${intent.email_choice}`;
    if (intent?.comfortable_editing_dns) command += ' --comfortable';
    if (intent?.registrar_known) command += ' --registrar-known';
    if (intent?.delegate_dns_management) command += ' --delegate-dns';

    const { stdout, stderr } = await execPromise(command);

    if (stderr && !stdout) {
      return NextResponse.json({ error: stderr }, { status: 500 });
    }

    const result = JSON.parse(stdout);
    return NextResponse.json(result);

  } catch (error: any) {
    console.error('Diagnosis error:', error);
    return NextResponse.json({ error: error.message }, { status: 500 });
  }
}
