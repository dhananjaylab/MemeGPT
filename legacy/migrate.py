#!/usr/bin/env python3
"""
MemeGPT v1 to v2 Migration Script

This script helps migrate from the old Streamlit-based MemeGPT to the new Next.js + FastAPI version.
It will:
1. Copy existing meme templates and fonts
2. Migrate meme_data.json to the new format
3. Set up the new project structure
4. Provide setup instructions
"""

import json
import shutil
import os
from pathlib import Path
from typing import Dict, Any, List

def ensure_directory(path: Path) -> None:
    """Create directory if it doesn't exist."""
    path.mkdir(parents=True, exist_ok=True)

def copy_templates_and_fonts() -> None:
    """Copy meme templates and fonts from the old structure."""
    print("📁 Copying templates and fonts...")
    
    # Copy templates
    old_templates = Path("templates")
    new_templates = Path("templates")
    
    if old_templates.exists():
        ensure_directory(new_templates)
        for template_file in old_templates.glob("*.jpg"):
            shutil.copy2(template_file, new_templates / template_file.name)
            print(f"   ✓ Copied {template_file.name}")
    else:
        print("   ⚠️  No templates directory found")
    
    # Copy fonts (if they exist)
    old_fonts = Path("fonts")
    new_fonts = Path("fonts")
    
    if old_fonts.exists():
        ensure_directory(new_fonts)
        for font_file in old_fonts.glob("*.ttf"):
            shutil.copy2(font_file, new_fonts / font_file.name)
            print(f"   ✓ Copied {font_file.name}")
    else:
        print("   ⚠️  No fonts directory found")

def migrate_meme_data() -> None:
    """Migrate meme_data.json to ensure compatibility."""
    print("📄 Migrating meme_data.json...")
    
    meme_data_path = Path("meme_data.json")
    
    if not meme_data_path.exists():
        print("   ⚠️  meme_data.json not found")
        return
    
    try:
        with open(meme_data_path, 'r', encoding='utf-8') as f:
            meme_data = json.load(f)
        
        # Validate and enhance the data structure
        enhanced_data = []
        
        for i, meme in enumerate(meme_data):
            # Ensure all required fields exist
            enhanced_meme = {
                "id": meme.get("id", i),
                "name": meme.get("name", f"Meme {i}"),
                "alternative_names": meme.get("alternative_names", []),
                "file_path": meme.get("file_path", ""),
                "font_path": meme.get("font_path", "impact.ttf"),
                "text_color": meme.get("text_color", "white"),
                "text_stroke": meme.get("text_stroke", True),
                "usage_instructions": meme.get("usage_instructions", ""),
                "number_of_text_fields": meme.get("number_of_text_fields", 2),
                "text_coordinates_xy_wh": meme.get("text_coordinates_xy_wh", []),
                "example_output": meme.get("example_output", [])
            }
            
            enhanced_data.append(enhanced_meme)
        
        # Write the enhanced data back
        with open(meme_data_path, 'w', encoding='utf-8') as f:
            json.dump(enhanced_data, f, indent=2, ensure_ascii=False)
        
        print(f"   ✓ Migrated {len(enhanced_data)} meme templates")
        
    except Exception as e:
        print(f"   ❌ Error migrating meme_data.json: {e}")

def create_env_files() -> None:
    """Create environment files from examples."""
    print("⚙️  Setting up environment files...")
    
    # Frontend env
    frontend_env_example = Path(".env.local.example")
    frontend_env = Path(".env.local")
    
    if frontend_env_example.exists() and not frontend_env.exists():
        shutil.copy2(frontend_env_example, frontend_env)
        print("   ✓ Created .env.local")
    
    # Backend env
    backend_env_example = Path("backend/.env.example")
    backend_env = Path("backend/.env")
    
    if backend_env_example.exists() and not backend_env.exists():
        shutil.copy2(backend_env_example, backend_env)
        print("   ✓ Created backend/.env")

def backup_old_files() -> None:
    """Backup old Streamlit files."""
    print("💾 Backing up old files...")
    
    backup_dir = Path("backup_v1")
    ensure_directory(backup_dir)
    
    old_files = [
        "app.py",
        "get_meme.py", 
        "meme_image_editor.py",
        "load_meme_data.py",
        "system_instructions.py",
        "requirements.txt"
    ]
    
    for file_name in old_files:
        old_file = Path(file_name)
        if old_file.exists():
            shutil.copy2(old_file, backup_dir / file_name)
            print(f"   ✓ Backed up {file_name}")

def print_next_steps() -> None:
    """Print instructions for completing the migration."""
    print("\n🎉 Migration completed!")
    print("\n📋 Next steps:")
    print("1. Install Node.js dependencies:")
    print("   npm install")
    print("\n2. Set up your API keys in the environment files:")
    print("   - Edit .env.local (frontend configuration)")
    print("   - Edit backend/.env (backend configuration)")
    print("   - At minimum, add your OPENAI_API_KEY")
    print("\n3. Start the development servers:")
    print("   Option A - Docker (recommended):")
    print("   docker compose up --build")
    print("\n   Option B - Local development:")
    print("   # Terminal 1: Start backend")
    print("   cd backend && python -m venv .venv && source .venv/bin/activate")
    print("   pip install -r requirements.txt")
    print("   uvicorn backend.main:app --reload")
    print("\n   # Terminal 2: Start frontend")
    print("   npm run dev")
    print("\n4. Visit http://localhost:3000 to see your new MemeGPT!")
    print("\n📚 For detailed setup instructions, see README-v2.md")

def main():
    """Run the migration process."""
    print("🧙 MemeGPT v1 → v2 Migration Tool")
    print("=" * 40)
    
    try:
        # Check if we're in the right directory
        if not Path("meme_data.json").exists() and not Path("app.py").exists():
            print("❌ This doesn't appear to be a MemeGPT v1 directory.")
            print("Please run this script from your MemeGPT project root.")
            return
        
        # Run migration steps
        backup_old_files()
        copy_templates_and_fonts()
        migrate_meme_data()
        create_env_files()
        
        print_next_steps()
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        print("Please check the error and try again, or migrate manually.")

if __name__ == "__main__":
    main()