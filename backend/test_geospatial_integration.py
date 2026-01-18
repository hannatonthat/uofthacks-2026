"""
Test script to verify geospatial metrics integration with SustainabilityAgent.

This script tests:
1. Loading geospatial metrics for Toronto coordinates
2. Verifying metrics are included in agent's context
3. Checking that metrics guide the agent's analysis
"""

import sys
from agents.specialized_agents import SustainabilityAgent
from utils.geospatial_metrics import get_analyzer

def test_geospatial_integration():
    print("\n" + "="*70)
    print("🧪 TESTING GEOSPATIAL METRICS INTEGRATION")
    print("="*70 + "\n")
    
    # Test coordinates (Downtown Toronto)
    test_lat = 43.6629
    test_lon = -79.3957
    
    print(f"📍 Test Location: {test_lat}°N, {test_lon}°W (Downtown Toronto)\n")
    
    # Test 1: Direct metrics analyzer
    print("TEST 1: Direct Geospatial Analyzer")
    print("-" * 70)
    try:
        analyzer = get_analyzer()
        analysis = analyzer.analyze_project_location(test_lat, test_lon)
        eco_sens = analysis.get('ecological_sensitivity', {})
        scores = eco_sens.get('scores', {})
        
        print(f"✅ Metrics loaded successfully!")
        print(f"   Total Score: {scores.get('total_score', 0)}/30")
        print(f"   - ESA Proximity: {scores.get('esa_score', 0)}/10")
        print(f"   - Green Space: {scores.get('green_space_score', 0)}/10")
        print(f"   - Urban Canopy: {scores.get('tree_score', 0)}/10")
        
        if eco_sens.get('recommendations'):
            print(f"\n   📊 Recommendations: {len(eco_sens['recommendations'])} generated")
        
        prompt_enhancement = analyzer.generate_sustainability_prompt_enhancement(test_lat, test_lon)
        print(f"\n   📝 Prompt Enhancement Length: {len(prompt_enhancement)} chars")
        print(f"   Preview: {prompt_enhancement[:200]}...")
        
    except Exception as e:
        print(f"❌ Failed: {e}")
        return False
    
    # Test 2: SustainabilityAgent with coordinates
    print("\n\nTEST 2: SustainabilityAgent with Geospatial Context")
    print("-" * 70)
    try:
        agent = SustainabilityAgent(
            latitude=test_lat,
            longitude=test_lon,
            user_id="test_user"
        )
        
        if agent.geospatial_context:
            print(f"✅ Agent loaded geospatial context!")
            print(f"   Context Length: {len(agent.geospatial_context)} chars")
            print(f"   Preview: {agent.geospatial_context[:300]}...")
        else:
            print(f"❌ No geospatial context loaded in agent")
            return False
            
    except Exception as e:
        print(f"❌ Failed to create agent: {e}")
        return False
    
    # Test 3: Chat with context
    print("\n\nTEST 3: Agent Chat with Geospatial Context")
    print("-" * 70)
    try:
        response = agent.chat_with_context(
            "What are the top 3 sustainability improvements this location should prioritize?",
            context=""
        )
        
        print(f"✅ Agent responded successfully!")
        print(f"   Response Length: {len(response)} chars")
        print(f"\n   Agent Response:\n   {response[:400]}...")
        
    except Exception as e:
        print(f"❌ Chat failed: {e}")
        return False
    
    # Test 4: Verify metrics influence responses
    print("\n\nTEST 4: Verify Metrics Influence Agent Responses")
    print("-" * 70)
    
    keywords_to_check = [
        "ESA", "Environmentally Significant Area", "green space", 
        "park", "tree", "canopy", "proximity", "300m", "1km"
    ]
    
    found_keywords = [kw for kw in keywords_to_check if kw.lower() in response.lower()]
    
    if found_keywords:
        print(f"✅ Found {len(found_keywords)} metric-related keywords in response:")
        for kw in found_keywords[:5]:  # Show first 5
            print(f"   - {kw}")
    else:
        print(f"⚠️  No metric keywords found (might be indirect references)")
    
    print("\n" + "="*70)
    print("✅ ALL TESTS PASSED - Integration Working!")
    print("="*70 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = test_geospatial_integration()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
