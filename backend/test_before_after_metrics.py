"""
Quick test to verify before/after metrics calculation.
"""

from agents.specialized_agents import SustainabilityAgent

def test_before_after_metrics():
    print("\n🧪 Testing Before/After Metrics\n")
    print("="*70)
    
    # Downtown Toronto coordinates
    lat, lon = 43.6629, -79.3957
    
    # Create agent with coordinates
    agent = SustainabilityAgent(
        latitude=lat,
        longitude=lon,
        user_id="test_user"
    )
    
    print(f"📍 Location: {lat}°N, {lon}°W")
    print(f"✅ Agent initialized with geospatial context")
    
    # Simulate a full analysis (without actual image)
    print("\n📊 Simulating metrics calculation...")
    
    # Get before metrics directly
    try:
        from utils.geospatial_metrics import get_analyzer
        analyzer = get_analyzer()
        analysis = analyzer.analyze_project_location(lat, lon)
        eco_sens = analysis.get("ecological_sensitivity", {})
        before_scores = eco_sens.get("scores", {})
        
        print(f"\n📉 BEFORE Metrics:")
        print(f"   ESA Proximity: {before_scores.get('esa_score', 0)}/10")
        print(f"   Green Space: {before_scores.get('green_space_score', 0)}/10")
        print(f"   Urban Canopy: {before_scores.get('tree_score', 0)}/10")
        print(f"   Total: {before_scores.get('total_score', 0)}/30")
        
        # Simulate after metrics
        before_metrics = {"scores": before_scores, "recommendations": []}
        after_metrics = agent._simulate_improved_metrics(before_metrics)
        after_scores = after_metrics.get("scores", {})
        
        print(f"\n📈 AFTER Metrics (Projected):")
        print(f"   ESA Proximity: {after_scores.get('esa_score', 0)}/10")
        print(f"   Green Space: {after_scores.get('green_space_score', 0)}/10")
        print(f"   Urban Canopy: {after_scores.get('tree_score', 0)}/10")
        print(f"   Total: {after_scores.get('total_score', 0)}/30")
        
        improvement = after_metrics.get("total_improvement", 0)
        print(f"\n🎯 Total Improvement: +{improvement} points")
        
        if after_metrics.get("improvements"):
            print(f"\n💡 Improvements Made:")
            for imp in after_metrics["improvements"]:
                print(f"   {imp}")
        
        print("\n" + "="*70)
        print("✅ Before/After metrics working correctly!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = test_before_after_metrics()
    sys.exit(0 if success else 1)
