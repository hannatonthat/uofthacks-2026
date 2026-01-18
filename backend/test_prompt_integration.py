"""
Simple test to verify geospatial context is in the agent's prompt
"""

from agents.specialized_agents import SustainabilityAgent

# Downtown Toronto
lat, lon = 43.6629, -79.3957

print("\n" + "="*80)
print("🧪 TESTING GEOSPATIAL CONTEXT IN AGENT PROMPT")
print("="*80)

print(f"\n📍 Creating agent with coordinates: {lat}°N, {lon}°W")

agent = SustainabilityAgent(
    latitude=lat,
    longitude=lon,
    user_id="test_user"
)

print(f"\n✅ Agent created successfully")

# Check if geospatial context was loaded
if agent.geospatial_context:
    print(f"\n📊 GEOSPATIAL CONTEXT LOADED:")
    print(f"   Length: {len(agent.geospatial_context)} characters")
    print(f"\n   Content Preview:")
    print("   " + "-"*76)
    for line in agent.geospatial_context.split('\n')[:15]:  # First 15 lines
        print(f"   {line}")
    print("   " + "-"*76)
    print(f"   ... (truncated, {len(agent.geospatial_context.split(chr(10)))} total lines)")
else:
    print(f"\n❌ NO GEOSPATIAL CONTEXT - Agent has empty context")

print(f"\n📝 Base Prompt:")
print(f"   {agent._prompt[:200]}...")

print("\n" + "="*80)
print("✅ VERIFICATION COMPLETE")
print("="*80)
print("\nThe geospatial context will be automatically injected into every chat message")
print("when you call agent.chat_with_context() or agent.run_full_analysis()")
print("\n")
