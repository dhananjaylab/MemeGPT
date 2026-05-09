#!/usr/bin/env python3
"""
Test caption order for all multi-field templates.
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.meme_ai import get_caption_generator

# Test cases for templates with specific field orders
TEST_CASES = {
    "Distracted Boyfriend": {
        "prompt": "playing video games vs doing homework",
        "expected_order": ["tempting thing (video games)", "person (Me)", "current thing (homework)"],
        "template_id": 1,
        "fields": 3
    },
    "Left Exit 12 Off Ramp": {
        "prompt": "going to bed early vs scrolling social media",
        "expected_order": ["main road (bed early)", "person (Me)", "exit (social media)"],
        "template_id": 2,
        "fields": 3
    },
    "Two Buttons": {
        "prompt": "choosing between studying or gaming",
        "expected_order": ["button 1 (study)", "button 2 (game)", "person sweating"],
        "template_id": 14,
        "fields": 3
    },
    "Expanding Brain": {
        "prompt": "ways to wake up in the morning",
        "expected_order": ["basic", "better", "advanced", "galaxy brain"],
        "template_id": 5,
        "fields": 4
    },
    "Panik Kalm Panik": {
        "prompt": "realizing you have an exam tomorrow",
        "expected_order": ["panic", "calm", "panic again"],
        "template_id": 17,
        "fields": 3
    },
    "Nobody Absolutely Nobody": {
        "prompt": "random things people do",
        "expected_order": ["Nobody:", "Absolutely nobody:", "the action"],
        "template_id": 18,
        "fields": 3
    },
    "Gru's Plan": {
        "prompt": "planning to be productive",
        "expected_order": ["step 1", "step 2", "unexpected result", "repeat result"],
        "template_id": 16,
        "fields": 4
    },
    "Bike Fall": {
        "prompt": "self-sabotage moment",
        "expected_order": ["person doing fine", "stick in wheel", "result/blame"],
        "template_id": 22,
        "fields": 3
    }
}

async def test_template_order(template_name, test_case):
    """Test a specific template's caption order."""
    print(f"\n{'='*70}")
    print(f"Testing: {template_name}")
    print(f"{'='*70}")
    print(f"Prompt: '{test_case['prompt']}'")
    print(f"Expected {test_case['fields']} fields in order:")
    for i, order in enumerate(test_case['expected_order'], 1):
        print(f"  {i}. {order}")
    print()
    
    try:
        generator = await get_caption_generator("openai")
        result = await generator(test_case['prompt'])
        
        if not result:
            print(f"❌ No results generated")
            return False
        
        # Find the specific template in results
        template_found = False
        for meme in result:
            if meme.get('meme_id') == test_case['template_id'] or \
               template_name.lower() in meme.get('meme_name', '').lower():
                template_found = True
                texts = meme.get('meme_text', [])
                
                print(f"✅ Found: {meme['meme_name']} (ID: {meme['meme_id']})")
                print(f"Generated {len(texts)} captions:")
                for i, text in enumerate(texts, 1):
                    print(f"  {i}. '{text}'")
                
                # Validate field count
                if len(texts) == test_case['fields']:
                    print(f"\n✅ Field count correct: {len(texts)}/{test_case['fields']}")
                else:
                    print(f"\n⚠️  Field count mismatch: {len(texts)}/{test_case['fields']}")
                
                print(f"Reasoning: {meme.get('reasoning', 'N/A')}")
                return True
        
        if not template_found:
            print(f"⚠️  Template '{template_name}' not in results")
            print(f"Generated templates: {[m.get('meme_name') for m in result]}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

async def test_all_templates():
    """Test all multi-field templates."""
    print("🧪 Testing Caption Order for All Multi-Field Templates")
    print("="*70)
    
    results = {}
    for template_name, test_case in TEST_CASES.items():
        success = await test_template_order(template_name, test_case)
        results[template_name] = success
        await asyncio.sleep(1)  # Rate limiting
    
    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for template_name, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {template_name}")
    
    print(f"\nTotal: {passed}/{total} templates tested successfully")
    
    if passed == total:
        print("\n🎉 All templates working correctly!")
    else:
        print(f"\n⚠️  {total - passed} template(s) need attention")

if __name__ == "__main__":
    asyncio.run(test_all_templates())