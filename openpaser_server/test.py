import asyncio
from client import OmniParserClient

async def test_omniparser():
    client = OmniParserClient()
    
    # Test cases
    test_cases = [
        {
            "image": "test_images/login_page.png",
            "task": "I want to login with username 'test@example.com' and password '12345'"
        },
        {
            "image": "test_images/dashboard.png",
            "task": "I want to navigate to the settings page"
        }
    ]
    
    for test in test_cases:
        print(f"\nTesting task: {test['task']}")
        print("-" * 50)
        
        try:
            # Get AI guidance
            guidance = await client.analyze_ui_elements(test["image"], test["task"])
            
            print("AI Assistant's Guidance:")
            print(guidance)
            print("-" * 50)
            
        except Exception as e:
            print(f"Error during test: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_omniparser()) 