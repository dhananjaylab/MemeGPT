#!/usr/bin/env python3
"""
Demonstration script showing the migration output.

This script shows exactly what data would be migrated from meme_data.json
to the database format, without requiring a database connection.

Usage:
    python demo_migration_output.py
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_meme_data_json() -> List[Dict[str, Any]]:
    """Load meme_data.json file."""
    backend_dir = Path(__file__).parent
    meme_data_path = backend_dir.parent / "meme_data.json"
    
    with open(meme_data_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def validate_meme_template(meme_data: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Validate and normalize a single meme template."""
    return {
        'id': meme_data.get('id', index),
        'name': str(meme_data['name']).strip(),
        'alternative_names': meme_data.get('alternative_names', []),
        'file_path': str(meme_data['file_path']).strip(),
        'font_path': str(meme_data['font_path']).strip(),
        'text_color': str(meme_data['text_color']).strip(),
        'text_stroke': bool(meme_data.get('text_stroke', False)),
        'usage_instructions': str(meme_data['usage_instructions']).strip(),
        'number_of_text_fields': int(meme_data['number_of_text_fields']),
        'text_coordinates_xy_wh': meme_data['text_coordinates_xy_wh'],
        'example_output': meme_data['example_output']
    }


def demonstrate_migration():
    """Demonstrate what the migration would do."""
    print("🧙 MemeGPT Template Migration Demonstration")
    print("=" * 60)
    
    # Load source data
    meme_data = load_meme_data_json()
    print(f"📄 Source: meme_data.json ({len(meme_data)} templates)")
    print(f"🎯 Target: PostgreSQL meme_templates table")
    print()
    
    # Show migration mapping
    print("🔄 Migration Mapping:")
    print("-" * 40)
    
    for i, template_data in enumerate(meme_data):
        validated = validate_meme_template(template_data, i)
        
        print(f"\n📋 Template {validated['id']}: {validated['name']}")
        print(f"   Alternative Names: {len(validated['alternative_names'])} aliases")
        print(f"   File Path: {validated['file_path']}")
        print(f"   Font: {validated['font_path']}")
        print(f"   Text Color: {validated['text_color']}")
        print(f"   Text Stroke: {validated['text_stroke']}")
        print(f"   Text Fields: {validated['number_of_text_fields']}")
        print(f"   Coordinates: {len(validated['text_coordinates_xy_wh'])} coordinate sets")
        print(f"   Example Output: {len(validated['example_output'])} examples")
        
        # Show a sample of the data
        if i < 2:  # Show details for first 2 templates
            print(f"   📝 Sample Data:")
            print(f"      Alternative Names: {validated['alternative_names']}")
            print(f"      Coordinates: {validated['text_coordinates_xy_wh']}")
            print(f"      Examples: {validated['example_output']}")
    
    print(f"\n📊 Migration Summary:")
    print(f"   Total Templates: {len(meme_data)}")
    print(f"   Total Text Fields: {sum(t['number_of_text_fields'] for t in [validate_meme_template(t, i) for i, t in enumerate(meme_data)])}")
    print(f"   Unique Names: {len(set(validate_meme_template(t, i)['name'] for i, t in enumerate(meme_data)))}")
    print(f"   File Formats: {len(set(validate_meme_template(t, i)['file_path'].split('.')[-1] for i, t in enumerate(meme_data)))}")
    
    # Show SQL that would be generated
    print(f"\n🗄️  Database Operations:")
    print("-" * 40)
    print("1. Clear existing templates: DELETE FROM meme_templates;")
    print(f"2. Insert {len(meme_data)} new templates:")
    
    for i, template_data in enumerate(meme_data[:3]):  # Show first 3 as examples
        validated = validate_meme_template(template_data, i)
        print(f"   INSERT INTO meme_templates (id, name, alternative_names, ...)")
        print(f"   VALUES ({validated['id']}, '{validated['name']}', '{json.dumps(validated['alternative_names'])}', ...);")
    
    if len(meme_data) > 3:
        print(f"   ... and {len(meme_data) - 3} more templates")
    
    print(f"\n✅ Migration would complete successfully!")
    print(f"   Result: {len(meme_data)} templates available in database")
    print(f"   Status: Ready for meme generation")


def show_template_details():
    """Show detailed information about each template."""
    print("\n\n📋 Detailed Template Information")
    print("=" * 60)
    
    meme_data = load_meme_data_json()
    
    for i, template_data in enumerate(meme_data):
        validated = validate_meme_template(template_data, i)
        
        print(f"\n🎭 Template {validated['id']}: {validated['name']}")
        print(f"   📁 File: {validated['file_path']}")
        print(f"   🔤 Font: {validated['font_path']}")
        print(f"   🎨 Text Color: {validated['text_color']}")
        print(f"   ✏️  Text Stroke: {'Yes' if validated['text_stroke'] else 'No'}")
        print(f"   📝 Text Fields: {validated['number_of_text_fields']}")
        
        if validated['alternative_names']:
            print(f"   🏷️  Alternative Names:")
            for alt_name in validated['alternative_names']:
                print(f"      - {alt_name}")
        
        print(f"   📐 Text Coordinates:")
        for j, coord in enumerate(validated['text_coordinates_xy_wh']):
            print(f"      Field {j+1}: x={coord[0]}, y={coord[1]}, w={coord[2]}, h={coord[3]}")
        
        print(f"   💡 Example Output:")
        for j, example in enumerate(validated['example_output']):
            print(f"      Field {j+1}: \"{example}\"")
        
        print(f"   📖 Usage Instructions:")
        # Wrap long instructions
        instructions = validated['usage_instructions']
        if len(instructions) > 80:
            words = instructions.split()
            lines = []
            current_line = []
            current_length = 0
            
            for word in words:
                if current_length + len(word) + 1 > 80:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
                else:
                    current_line.append(word)
                    current_length += len(word) + 1
            
            if current_line:
                lines.append(' '.join(current_line))
            
            for line in lines:
                print(f"      {line}")
        else:
            print(f"      {instructions}")


def main():
    """Main demonstration function."""
    try:
        demonstrate_migration()
        
        # Ask if user wants to see detailed template information
        print(f"\n❓ Would you like to see detailed template information? (y/n): ", end="")
        try:
            response = input().strip().lower()
            if response in ['y', 'yes']:
                show_template_details()
        except (EOFError, KeyboardInterrupt):
            pass
        
        print(f"\n🎉 Migration demonstration complete!")
        print(f"\nTo perform the actual migration:")
        print(f"1. Ensure PostgreSQL is running")
        print(f"2. Run: python migrate_meme_templates.py --dry-run")
        print(f"3. Run: python migrate_meme_templates.py --backup")
        
    except Exception as e:
        print(f"❌ Demonstration failed: {e}")
        return False
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Demonstration cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)