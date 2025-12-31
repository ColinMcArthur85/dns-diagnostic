# DNS & Email Delivery Diagnostic Tool

A comprehensive tool for analyzing domain connectivity, email deliverability, and platform-specific DNS requirements.

## Deployment

This project is optimized for **Vercel**. It uses a hybrid architecture with a Next.js frontend and native Python serverless functions for the diagnostic logic.

1.  Push this repository to GitHub.
2.  Import the project into Vercel.
3.  Add `OPENAI_API_KEY` to your Vercel Environment Variables.
4.  Deploy!

## Project Structure (Vercel Optimized)

- `/api`: Native Python serverless functions (diagnose, chat).
- `/src`: Next.js frontend (components, pages, styles).
- `/logic`: Core Python diagnostic engine (standalone modules).
- `domain_rules.yaml`: Single source of truth for platform DNS requirements.
- `requirements.txt`: Python dependencies for the Vercel runtime.

---

## Technical Stack

- **Frontend**: Next.js 15, React 19, Tailwind CSS v4, Framer Motion
- **Backend API**: Native Vercel Python Functions
- **Diagnostic Engine**: Python 3 (dnspython, whois, tldextract)
- **AI Integration**: OpenAI GPT-4o-mini
