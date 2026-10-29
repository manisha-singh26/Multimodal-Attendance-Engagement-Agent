"""Production WSGI Server Entry Point using Waitress.
Provides multi-threaded, robust offline serving suitable for classroom appliances or edge servers.
"""
import os
import sys
from waitress import serve
from app.server import app

def main():
    port = int(os.environ.get("PORT", 5000))
    threads = int(os.environ.get("THREADS", 6))
    
    print("=" * 70)
    print("🎓 MULTIMODAL CLASSROOM INTELLIGENCE AGENT - PRODUCTION SERVER")
    print("=" * 70)
    print(f"🚀 Serving on http://0.0.0.0:{port} with {threads} worker threads")
    print(f"🔒 100% Offline Edge Mode - Local Database: db/classroom_intel.db")
    print("=" * 70)
    
    serve(app, host="0.0.0.0", port=port, threads=threads)

if __name__ == "__main__":
    main()

