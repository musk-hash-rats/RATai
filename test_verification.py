import asyncio
import os
from utils.database import init_db, add_xp, get_user_data, get_top_users, add_reaction_count, get_reaction_count
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

async def test_db():
    print("--- Testing Database ---")
    await init_db()
    print("DB Initialized.")
    
    # Test Adding XP
    user_id = 12345
    guild_id = 999
    
    await add_xp(user_id, guild_id, 100)
    data = await get_user_data(user_id, guild_id)
    print(f"User Data (should be ~100xp, lv2): {data}")
    assert data[0] == 100
    
    # Test Reactions
    await add_reaction_count(user_id, guild_id)
    count = await get_reaction_count(user_id, guild_id)
    print(f"Reaction Count (should be 1): {count}")
    assert count == 1
    
    # Test Leaderboard
    top = await get_top_users(guild_id)
    print(f"Top Users: {top}")
    assert len(top) > 0
    print("DB Tests Passed!\n")

def test_sentiment():
    print("--- Testing Sentiment Logic ---")
    analyzer = SentimentIntensityAnalyzer()
    
    texts = [
        "I love this amazing bot!", # Positive High Intensity
        "I hate you so much!",       # Negative High Intensity
        "This is a message.",        # Neutral
    ]
    
    for text in texts:
        scores = analyzer.polarity_scores(text)
        compound = scores['compound']
        intensity = abs(compound)
        
        multiplier = 2.0 if intensity >= 0.5 else 0.5
        print(f"Text: '{text}' | Compound: {compound:.2f} | Intensity: {intensity:.2f} | Mult: {multiplier}x")
        
        if "love" in text or "hate" in text:
            assert multiplier == 2.0
        else:
            assert multiplier == 0.5
    print("Sentiment Tests Passed!\n")

async def main():
    if os.path.exists("data/database.db"):
        os.remove("data/database.db")
        print("Cleaned up old database.")

    test_sentiment()
    await test_db()

if __name__ == "__main__":
    asyncio.run(main())
