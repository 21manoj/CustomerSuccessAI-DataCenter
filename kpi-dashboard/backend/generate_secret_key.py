#!/usr/bin/env python3
"""
Generate cryptographically secure SECRET_KEY for Flask application
"""

import secrets
import os
from datetime import datetime
from pathlib import Path

def generate_secret_key(length=32):
    """Generate a cryptographically secure secret key"""
    return secrets.token_hex(length)

def create_env_file(environment='development'):
    """Create .env file with generated keys"""
    
    secret_key = generate_secret_key(32)
    
    env_content = f"""# Generated on {datetime.now().isoformat()}
# Environment: {environment}

# CRITICAL: Never commit this file to version control!
# Add .env to .gitignore

# Flask Secret Key (for session signing)
SECRET_KEY={secret_key}

# Database URL
DATABASE_URL=sqlite:///instance/kpi_dashboard.db

# Environment
FLASK_ENV={environment}
DEBUG={'True' if environment == 'development' else 'False'}

# Session Configuration  
SESSION_TYPE=sqlalchemy
SESSION_PERMANENT=True
SESSION_COOKIE_SECURE={'False' if environment == 'development' else 'True'}

# OpenAI API Key (if using RAG)
# OPENAI_API_KEY=your-key-here
"""
    
    env_file = Path('.env')
    
    if env_file.exists():
        response = input(f".env already exists. Overwrite? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Cancelled. Existing .env preserved.")
            return None
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Created .env file for {environment}")
    print(f"✅ Generated SECRET_KEY: {secret_key[:16]}...{secret_key[-8:]}")
    print(f"\n⚠️  IMPORTANT: Add .env to .gitignore!")
    print(f"⚠️  NEVER commit secret keys to version control!")
    
    return secret_key

def create_env_example():
    """Create .env.example template"""
    
    example_content = """# Environment Configuration Template
# Copy this file to .env and fill in actual values
# NEVER commit .env to version control!

# Flask Secret Key (REQUIRED)
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your-secret-key-here-minimum-32-characters

# Database
DATABASE_URL=sqlite:///instance/kpi_dashboard.db

# Environment
FLASK_ENV=development
DEBUG=True

# Session Configuration
SESSION_TYPE=sqlalchemy
SESSION_PERMANENT=True
SESSION_COOKIE_SECURE=False

# OpenAI API Key (for RAG system)
OPENAI_API_KEY=your-openai-api-key

# Email Configuration (optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-app-password
"""
    
    with open('.env.example', 'w') as f:
        f.write(example_content)
    
    print("✅ Created .env.example template")

def verify_gitignore():
    """Verify .gitignore includes .env"""
    gitignore = Path('.gitignore')
    
    if not gitignore.exists():
        print("⚠️  .gitignore doesn't exist, creating...")
        with open(gitignore, 'w') as f:
            f.write("# Environment variables\n.env\n.env.local\n*.env\n")
        print("✅ Created .gitignore with .env")
        return
    
    with open(gitignore, 'r') as f:
        content = f.read()
    
    if '.env' not in content:
        print("⚠️  .gitignore doesn't include .env, adding...")
        with open(gitignore, 'a') as f:
            f.write("\n# Environment variables\n.env\n.env.local\n*.env\n")
        print("✅ Added .env to .gitignore")
    else:
        print("✅ .gitignore already includes .env")

if __name__ == '__main__':
    import sys
    
    print("=" * 70)
    print("SECRET KEY GENERATOR FOR FLASK APPLICATION")
    print("=" * 70)
    
    # Ask for environment
    print("\nWhich environment are you setting up?")
    print("  1. Development (local)")
    print("  2. Production (AWS)")
    print("  3. Just show me a secret key")
    
    choice = input("\nChoice (1/2/3): ").strip()
    
    if choice == '1':
        # Development setup
        print("\n📋 Setting up DEVELOPMENT environment...")
        secret_key = create_env_file('development')
        create_env_example()
        verify_gitignore()
        
        if secret_key:
            print("\n" + "=" * 70)
            print("✅ DEVELOPMENT SETUP COMPLETE")
            print("=" * 70)
            print("\nYour application is now configured with a secure SECRET_KEY.")
            print("Start the application with: python backend/app_v3_minimal.py")
    
    elif choice == '2':
        # Production - just generate key
        print("\n📋 PRODUCTION SECRET KEY")
        print("=" * 70)
        secret_key = generate_secret_key(32)
        print(f"\nGenerated production SECRET_KEY:")
        print(f"{secret_key}")
        print("\n⚠️  CRITICAL SECURITY INSTRUCTIONS:")
        print("1. Copy the SECRET_KEY above")
        print("2. Set it as environment variable on AWS:")
        print(f"   export SECRET_KEY={secret_key}")
        print("3. Or add to docker-compose.yml")
        print("4. NEVER commit this key to version control")
        print("5. Store securely (AWS Secrets Manager, 1Password, etc.)")
        print("=" * 70)
    
    elif choice == '3':
        # Just generate and display
        secret_key = generate_secret_key(32)
        print(f"\n🔑 Generated SECRET_KEY:\n{secret_key}")
        print("\nUse this key in your environment configuration.")
    
    else:
        print("Invalid choice. Run script again.")
        sys.exit(1)

