import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.game_engine import GameEngine

async def test_all_functions():
    print("=" * 60)
    print("修仙世界 - 功能测试")
    print("=" * 60)
    
    engine = GameEngine()
    await engine.initialize()
    
    print("\n1. 测试游戏启动...")
    result = await engine.start_game()
    print(f"   ✓ 游戏启动成功")
    print(f"   当前位置：{engine.game_state.current_location}")
    
    print("\n2. 测试NPC生成...")
    spawn_result = await engine.spawn_random_npc("散修")
    print(f"   ✓ NPC生成成功：{spawn_result.get('npc_name', '未知')}")
    
    print("\n3. 测试NPC列表...")
    npcs = engine.get_all_npcs()
    print(f"   ✓ 当前NPC数量：{len(npcs)}")
    for npc_id, npc in npcs.items():
        print(f"     - {npc.name} ({npc_id})")
    
    print("\n4. 测试世界事件...")
    event_result = await engine.trigger_dynamic_world()
    print(f"   ✓ 世界事件触发成功：{event_result.get('message', '未知')}")
    
    print("\n5. 测试玩家输入...")
    input_result = await engine.process_player_input("观察四周", "custom")
    print(f"   ✓ 玩家输入处理成功")
    
    print("\n6. 测试任务系统...")
    quest_result = await engine.get_quests()
    print(f"   ✓ 任务系统正常")
    print(f"     进行中：{quest_result.get('summary', {}).get('active_count', 0)} 个")
    print(f"     已完成：{quest_result.get('summary', {}).get('completed_count', 0)} 个")
    
    print("\n7. 测试NPC对话...")
    if npcs:
        first_npc_id = list(npcs.keys())[0]
        npc = engine.get_npc_by_id(first_npc_id)
        if npc:
            from core.dialogue_manager import DialogueManager
            dialogue_manager = DialogueManager(
                engine.ai_service,
                engine.memory_manager,
                engine.narrator
            )
            context = engine._build_context()
            dialogue_result = await dialogue_manager.start_dialogue(npc, context)
            print(f"   ✓ NPC对话成功：{npc.name}")
    
    print("\n8. 测试特殊NPC生成...")
    special_result = await engine.spawn_special_npc("时间操控者")
    print(f"   ✓ 特殊NPC生成成功：{special_result.get('npc_name', '未知')}")
    
    print("\n9. 测试NPC群体生成...")
    group_result = await engine.spawn_npc_group(2)
    print(f"   ✓ NPC群体生成成功：{len(group_result.get('npcs', []))} 个")
    
    print("\n10. 测试游戏状态...")
    state = engine.game_state.to_dict()
    print(f"   ✓ 游戏状态正常")
    print(f"     位置：{state.get('current_location', '未知')}")
    print(f"     时间：{state.get('world_time', '未知')}")
    print(f"     天气：{state.get('weather', '未知')}")
    
    await engine.close()
    
    print("\n" + "=" * 60)
    print("所有测试完成！")
    print("=" * 60)

if __name__ == "__main__":
    try:
        asyncio.run(test_all_functions())
    except KeyboardInterrupt:
        print("\n\n测试已中断。")
        sys.exit(0)
    except Exception as e:
        print(f"\n\n测试失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)