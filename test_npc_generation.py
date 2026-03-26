import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.ai_service import AIService
from memory.memory_manager import MemoryManager
from agents.npc_generator import NPCGenerator

async def test_npc_generation():
    print("=" * 50)
    print("NPC随机生成测试")
    print("=" * 50)
    
    ai_service = AIService()
    await ai_service.__aenter__()
    
    memory_manager = MemoryManager()
    
    generator = NPCGenerator(ai_service, memory_manager)
    
    print("\n测试1：生成普通NPC")
    print("-" * 50)
    npc1 = await generator.generate_npc("起始村庄", "村庄广场，阳光明媚", "commoner")
    print(f"NPC ID: {npc1.npc_id}")
    print(f"姓名: {npc1.name}")
    print(f"性格: {npc1.personality}")
    print(f"背景: {npc1.background}")
    print(f"目标: {', '.join(npc1.goals)}")
    
    print("\n测试2：生成NPC群体")
    print("-" * 50)
    npcs = await generator.generate_npc_group("森林", "神秘的森林深处", 3)
    print(f"生成了 {len(npcs)} 个NPC:")
    for i, npc in enumerate(npcs, 1):
        print(f"\n  NPC {i}:")
        print(f"    姓名: {npc.name}")
        print(f"    性格: {npc.personality}")
    
    print("\n测试3：生成特殊NPC")
    print("-" * 50)
    special_npc = await generator.generate_special_npc("城镇", "繁华的市集", "神秘旅行者")
    print(f"特殊NPC ID: {special_npc.npc_id}")
    print(f"姓名: {special_npc.name}")
    print(f"性格: {special_npc.personality}")
    print(f"背景: {special_npc.background}")
    print(f"特殊能力: {getattr(special_npc, 'special_abilities', [])}")
    
    print("\n测试4：获取地点NPC类型")
    print("-" * 50)
    for location in ["起始村庄", "森林", "城镇", "山脉", "海岸"]:
        npc_types = generator.get_npc_types_for_location(location)
        print(f"{location}: {', '.join(npc_types)}")
    
    await ai_service.close()
    
    print("\n" + "=" * 50)
    print("✓ NPC生成测试完成！")
    print("=" * 50)

if __name__ == "__main__":
    try:
        asyncio.run(test_npc_generation())
    except KeyboardInterrupt:
        print("\n\n测试已中断。")
        sys.exit(0)