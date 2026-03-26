import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ai_service import AIService
from memory.memory_manager import MemoryManager
from utils.config import config

async def test_ai_service():
    print("测试AI服务...")
    
    async with AIService() as ai_service:
        try:
            response = await ai_service.generate_response(
                system_prompt="你是一个测试助手。",
                user_message="请说'测试成功'"
            )
            print(f"AI响应：{response}")
            print("✓ AI服务测试通过")
            return True
        except Exception as e:
            print(f"✗ AI服务测试失败：{e}")
            return False

async def test_memory_manager():
    print("\n测试记忆管理器...")
    
    try:
        memory_manager = MemoryManager()
        
        memory_manager.add_short_term("user", "测试消息")
        context = memory_manager.get_context_for_ai()
        print(f"短期记忆：{context}")
        
        memory_manager.add_long_term(
            content="这是一个重要的测试记忆",
            memory_type="test",
            importance=8,
            participants=["player"],
            context="测试上下文"
        )
        
        memories = memory_manager.search_memories("测试", limit=5)
        print(f"找到 {len(memories)} 条记忆")
        
        print("✓ 记忆管理器测试通过")
        return True
    except Exception as e:
        print(f"✗ 记忆管理器测试失败：{e}")
        import traceback
        traceback.print_exc()
        return False

async def test_config():
    print("测试配置加载...")
    
    try:
        api_config = config.get_api_config()
        print(f"API配置：{api_config}")
        
        game_config = config.get_game_config()
        print(f"游戏配置：{game_config}")
        
        print("✓ 配置加载测试通过")
        return True
    except Exception as e:
        print(f"✗ 配置加载测试失败：{e}")
        return False

async def main():
    print("=" * 50)
    print("AI游戏系统测试")
    print("=" * 50)
    
    results = []
    
    results.append(await test_config())
    results.append(await test_memory_manager())
    results.append(await test_ai_service())
    
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    
    passed = sum(results)
    total = len(results)
    
    print(f"通过：{passed}/{total}")
    
    if passed == total:
        print("\n✓ 所有测试通过！游戏系统已准备就绪。")
        print("\n运行 'python main.py' 开始游戏。")
    else:
        print(f"\n✗ 有 {total - passed} 个测试失败，请检查配置。")

if __name__ == "__main__":
    asyncio.run(main())