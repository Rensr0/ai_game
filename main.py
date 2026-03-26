import asyncio
import sys
from core.game_engine import GameEngine
from agents.npc_agent import NPCAgent
from core.dialogue_manager import DialogueManager
from utils.config import config


class AIGameCLI:
    def __init__(self):
        self.engine = None
        self.dialogue_manager = None
        self.running = False

    async def initialize(self):
        print("正在初始化AI游戏系统...")

        self.engine = GameEngine()
        await self.engine.initialize()

        self.dialogue_manager = DialogueManager(
            self.engine.ai_service,
            self.engine.memory_manager,
            self.engine.narrator
        )

        await self._setup_initial_npcs()

        print("初始化完成！\n")

    async def _setup_initial_npcs(self):
        print("正在生成初始NPC...")

        context = self.engine._build_context()

        spawn_result = await self.engine.spawn_npc_group(count=3)

        if spawn_result.get("npcs"):
            npc_names = [npc["npc_name"] for npc in spawn_result["npcs"]]
            print(f"已生成 {len(npc_names)} 个NPC：{', '.join(npc_names)}")

    async def start(self):
        await self.initialize()

        print("=" * 60)
        print("⚔️ 欢迎来到修仙世界 - AI文字冒险游戏")
        print("=" * 60)
        print()

        start_result = await self.engine.start_game()

        if start_result.get("narration"):
            print(start_result["narration"])
            print()

        state = start_result.get("world_state", {})
        print(f"📍 当前位置：{state.get('current_location', '未知')}")
        print(f"🕐 时间：{state.get('world_time', '未知')}")
        print(f"🌤 天气：{state.get('weather', '未知')}")

        cult = state.get("cultivation", {})
        print(f"⭐ 境界：{cult.get('realm_name', '炼气·1层')}")
        print()

        self.running = True
        await self.game_loop()

    async def game_loop(self):
        current_dialogue_id = None
        in_combat = False

        while self.running:
            try:
                if in_combat:
                    print("\n[⚔️ 战斗中]")
                    print("  攻击 - 普通攻击")
                    print("  技能 <名称> - 使用技能")
                    print("  防御 - 防御姿态")
                    print("  丹药 - 使用丹药")
                    print("  逃跑 - 尝试逃跑")
                elif current_dialogue_id:
                    print("\n[💬 对话中]")
                    print("输入你的回应，或输入 '结束' 结束对话")
                else:
                    print("\n[🗺️ 探索模式]")
                    print("  对话 - 与附近的NPC对话")
                    print("  战斗 - 进入战斗")
                    print("  修炼 - 打坐修炼")
                    print("  移动 <地点> - 前往新地点")
                    print("  地图 - 查看当前区域信息")
                    print("  任务 - 查看任务列表")
                    print("  状态 - 查看当前状态")
                    print("  背包 - 查看背包物品")
                    print("  商店 - 打开商店")
                    print("  保存 - 保存游戏进度")
                    print("  帮助 - 显示帮助")
                    print("  退出 - 退出游戏")

                user_input = input("\n> ").strip()

                if not user_input:
                    continue

                # 退出
                if user_input.lower() in ["退出", "exit", "quit"]:
                    await self.exit_game()
                    break

                # 帮助
                if user_input.lower() in ["帮助", "help"]:
                    self.show_help()
                    continue

                # ====== 战斗中 ======
                if in_combat:
                    if user_input.lower() in ["攻击", "普通攻击"]:
                        result = self.engine.execute_combat_turn("attack")
                    elif user_input.lower() == "防御":
                        result = self.engine.execute_combat_turn("defend")
                    elif user_input.lower() in ["丹药", "使用丹药"]:
                        result = self.engine.execute_combat_turn("use_item")
                    elif user_input.lower() in ["逃跑", "逃"]:
                        result = self.engine.execute_combat_turn("flee")
                    elif user_input.lower().startswith("技能 "):
                        skill_name = user_input[3:].strip()
                        result = self.engine.execute_combat_turn("skill", skill_name)
                    else:
                        print("无效的战斗指令，请输入：攻击/技能/防御/丹药/逃跑")
                        continue

                    # 打印战斗日志
                    for line in result.get("log", []):
                        print(f"  {line}")

                    if result.get("status") in ["victory", "defeat", "fled"]:
                        in_combat = False
                        self.engine.end_combat()
                        if result.get("status") == "victory":
                            print("\n🎉 战斗胜利！")
                        elif result.get("status") == "defeat":
                            print("\n💀 战斗失败...")
                        else:
                            print("\n🏃 成功逃跑！")
                    continue

                # ====== 对话中 ======
                if current_dialogue_id:
                    if user_input.lower() in ["结束", "end"]:
                        self.dialogue_manager.end_dialogue(current_dialogue_id)
                        current_dialogue_id = None
                        print("对话结束。")
                        continue

                    dialogue_result = await self.dialogue_manager.process_custom_input(
                        current_dialogue_id, user_input
                    )

                    print(f"\n{dialogue_result.get('npc_name', 'NPC')}：{dialogue_result.get('npc_response', '')}")

                    if dialogue_result.get('relationship_change', 0) != 0:
                        change = dialogue_result['relationship_change']
                        status = "改善" if change > 0 else "恶化"
                        print(f"💕 关系{status}（当前：{dialogue_result.get('relationship', 0)}）")

                    if dialogue_result.get('dialogue_options'):
                        print("\n可选回应：")
                        for i, option in enumerate(dialogue_result['dialogue_options'], 1):
                            print(f"  {i}. {option}")

                    if dialogue_result.get('dialogue_ended'):
                        if 'closing_message' in dialogue_result:
                            print(f"\n{dialogue_result['closing_message']}")
                        current_dialogue_id = None

                    continue

                # ====== 探索模式命令 ======
                # 对话
                if user_input.lower() in ["对话", "talk", "dialogue"]:
                    await self.start_dialogue()
                    continue

                # 战斗
                if user_input.lower() in ["战斗", "combat", "fight"]:
                    await self.start_combat_cli()
                    in_combat = self.engine.get_combat_status() is not None
                    continue

                # 修炼
                if user_input.lower() in ["修炼", "打坐", "meditate"]:
                    print("\n🧘 你盘膝而坐，开始打坐修炼...")
                    result = self.engine.meditate()
                    print(f"📊 获得 {result['exp_gained']} 修炼经验")
                    print(f"💧 恢复 {result['mp_restored']} 灵力")
                    if result.get('exp_result', {}).get('breakthrough'):
                        print(f"🎉 突破成功！当前境界：{result['exp_result']['new_realm']}")
                    continue

                # 移动
                if user_input.lower().startswith("移动 "):
                    target = user_input[3:].strip()
                    print(f"\n🚶 正在前往 {target}...")
                    result = await self.engine.move_to_location(target)
                    if result.get("error"):
                        print(f"❌ {result['error']}")
                    else:
                        if result.get("narration"):
                            print(f"\n{result['narration']}")
                        if result.get("encounter") and result["encounter"].get("type") == "combat":
                            enemy = result["encounter"]["enemy"]
                            print(f"\n⚔️ 遭遇了 {enemy['name']}！")
                            confirm = input("进入战斗？(y/n): ").strip().lower()
                            if confirm in ["y", "yes", "是", ""]:
                                self.engine.start_combat(enemy)
                                in_combat = True
                                print("⚔️ 战斗开始！")
                    continue

                # 地图
                if user_input.lower() in ["地图", "map"]:
                    map_info = self.engine.get_map_info()
                    region = map_info.get("region", {})
                    print(f"\n📍 当前位置：{map_info.get('current_location')}")
                    print(f"📝 {region.get('description', '')}")
                    print(f"⚠️ 危险等级：{'⭐' * region.get('danger_level', 1)}")
                    connections = region.get("connections", [])
                    if connections:
                        print(f"🔗 可前往：{', '.join(connections)}")
                    continue

                # 任务
                if user_input.lower() in ["任务", "quest", "任务列表"]:
                    await self.show_quests()
                    continue

                # 状态
                if user_input.lower() in ["状态", "status", "状态信息"]:
                    await self.show_status()
                    continue

                # 背包
                if user_input.lower() in ["背包", "inventory", "物品", "inv"]:
                    self.show_inventory()
                    continue

                # 商店
                if user_input.lower() in ["商店", "shop"]:
                    self.show_shop()
                    continue

                # NPC相关
                if user_input.lower() in ["生成npc", "spawn_npc", "生成"]:
                    await self.spawn_random_npc()
                    continue
                if user_input.lower() in ["生成特殊npc", "spawn_special"]:
                    await self.spawn_special_npc()
                    continue
                if user_input.lower() in ["世界事件", "world_event", "事件"]:
                    await self.trigger_world_event()
                    continue
                if user_input.lower() in ["查看npc", "list_npcs", "npc列表"]:
                    await self.list_npcs()
                    continue

                # 保存
                if user_input.lower() in ["保存", "save", "存档"]:
                    await self.save_game()
                    continue

                # 新游戏
                if user_input.lower() in ["新游戏", "new_game", "重新开始"]:
                    await self.new_game()
                    continue

                # 自由输入 - 处理行动
                result = await self.engine.process_player_input(user_input, "custom")

                if result.get("narration"):
                    print(f"\n{result['narration']}")

                if result.get("world_description"):
                    print(f"\n{result['world_description']}")

                if result.get("new_quest"):
                    quest = result['new_quest']['quest']
                    print(f"\n📜 [新任务] {quest['title']}")
                    print(f"   {quest['description']}")

                if result.get("breakthrough"):
                    print(f"\n🎉 {result['breakthrough']['message']}")

                # 检查遭遇
                if result.get("encounter") and result["encounter"].get("type") == "combat":
                    enemy = result["encounter"]["enemy"]
                    print(f"\n⚔️ 遭遇了 {enemy['name']}！")
                    confirm = input("进入战斗？(y/n): ").strip().lower()
                    if confirm in ["y", "yes", "是", ""]:
                        self.engine.start_combat(enemy)
                        in_combat = True

            except KeyboardInterrupt:
                print("\n\n检测到中断信号...")
                await self.exit_game()
                break
            except Exception as e:
                print(f"\n❌ 发生错误：{e}")
                import traceback
                traceback.print_exc()

    async def start_combat_cli(self):
        print("\n正在生成敌人...")
        import random
        region = self.engine.get_map_info().get("region", {})
        danger = region.get("danger_level", 1)
        enemy_types = {1: ["妖兽"], 2: ["妖兽", "灵兽"], 3: ["灵兽", "魔修"],
                       4: ["魔修"], 5: ["灵兽"], 6: ["妖王"], 7: ["守护者"]}
        possible = enemy_types.get(danger, ["妖兽"])
        enemy_type = random.choice(possible)
        entity = self.engine.combat_system.create_enemy(enemy_type, danger)

        result = self.engine.start_combat(entity.to_dict())

        for line in result.get("log", []):
            print(f"  {line}")
        print(f"\n{entity.name} - ❤️{entity.hp} ⚔️{entity.attack} 🛡️{entity.defense}")

    async def start_dialogue(self):
        nearby_npcs = self.engine._get_nearby_npcs()

        if not nearby_npcs:
            print("\n附近没有可以对话的NPC。")
            return

        print("\n附近的NPC：")
        for i, npc_id in enumerate(nearby_npcs, 1):
            if npc_id in self.engine.npcs:
                npc = self.engine.npcs[npc_id]
                print(f"  {i}. {npc.name}")

        choice = input("\n选择要对话的NPC（输入序号）：").strip()

        try:
            index = int(choice) - 1
            if 0 <= index < len(nearby_npcs):
                npc_id = nearby_npcs[index]
                if npc_id in self.engine.npcs:
                    npc = self.engine.npcs[npc_id]
                    context = self.engine._build_context()

                    result = await self.dialogue_manager.start_dialogue(npc, context)

                    print(f"\n{result['npc_name']}：{result['opening_message']}")
                    print(f"💕 关系状态：{result.get('relationship', 0)}")

                    if result.get("dialogue_options"):
                        print("\n可选回应：")
                        for i, option in enumerate(result['dialogue_options'], 1):
                            print(f"  {i}. {option}")
            else:
                print("无效的选择。")
        except ValueError:
            print("请输入有效的数字。")

    def show_inventory(self):
        inv = self.engine.game_state.inventory
        equip = self.engine.game_state.equipment

        print("\n" + "=" * 40)
        print("🎒 背包")
        print("=" * 40)

        if inv:
            counts = {}
            for item in inv:
                counts[item] = counts.get(item, 0) + 1
            for item, count in counts.items():
                info = self.engine.item_system.get_item_info(item)
                rarity = info.get("rarity", "common") if info else "common"
                rarity_names = {"common": "普通", "uncommon": "优秀", "rare": "稀有", "epic": "史诗", "legendary": "传说"}
                print(f"  {'📦'} {item} x{count} [{rarity_names.get(rarity, '普通')}]")
                if info:
                    print(f"     {info.get('description', '')}")
        else:
            print("  空空如也...")

        print(f"\n🗡️ 武器：{equip.get('weapon') or '无'}")
        print(f"🛡️ 护甲：{equip.get('armor') or '无'}")

    def show_shop(self):
        items = self.engine.get_shop_items()
        gold = self.engine.game_state.stats["gold"]

        print(f"\n{'=' * 40}")
        print(f"🏪 修仙商店 (💰 {gold} 金币)")
        print("=" * 40)

        for i, item in enumerate(items, 1):
            rarity_names = {"common": "普通", "uncommon": "优秀", "rare": "稀有", "epic": "史诗", "legendary": "传说"}
            print(f"  {i}. {item['name']} [{rarity_names.get(item.get('rarity', 'common'), '普通')}] - 💰{item.get('price', 0)}")
            print(f"     {item.get('description', '')}")

        print("\n输入 '购买 <物品名>' 购买，'出售 <物品名>' 出售")

    async def show_quests(self):
        quests = await self.engine.get_quests()

        print("\n" + "=" * 40)
        print("📜 任务列表")
        print("=" * 40)

        if quests.get("active"):
            print("\n进行中的任务：")
            for quest in quests["active"]:
                print(f"\n  [{quest['id']}] {quest['title']}")
                print(f"  描述：{quest['description']}")
                print(f"  进度：{quest['progress']}%")
                if quest.get('objectives'):
                    print(f"  目标：{', '.join(quest['objectives'])}")

        if quests.get("completed"):
            print("\n已完成的任务：")
            for quest in quests["completed"]:
                print(f"\n  [{quest['id']}] {quest['title']} ✅")

        print(f"\n总计：{quests['summary']['active_count']} 个进行中，{quests['summary']['completed_count']} 个已完成")

    async def show_status(self):
        state = self.engine.game_state
        cult = state.cultivation
        total = state.get_total_stats()

        print("\n" + "=" * 40)
        print("📊 当前状态")
        print("=" * 40)
        print(f"玩家：{state.player_name}")
        print(f"📍 位置：{state.current_location}")
        print(f"🕐 时间：{state.world_time}")
        print(f"🌤 天气：{state.weather}")
        print(f"\n⭐ 修仙境界：{cult.full_realm}")
        print(f"  经验：{cult.experience}/{cult.exp_to_next}")
        print(f"  灵石：{cult.spirit_stones}")
        print(f"\n属性：")
        print(f"  ❤️ 生命值：{total['health']}")
        print(f"  💧 灵力：{total['mana']}")
        print(f"  ⚔️ 攻击：{total['attack']}")
        print(f"  🛡️ 防御：{total['defense']}")
        print(f"  💰 金币：{total['gold']}")
        print(f"\n技能：{', '.join(cult.skills) or '无'}")
        print(f"🗡️ 武器：{state.equipment.get('weapon') or '无'}")
        print(f"🛡️ 护甲：{state.equipment.get('armor') or '无'}")

    def show_help(self):
        print("\n" + "=" * 40)
        print("❓ 帮助")
        print("=" * 40)
        print("\n基本命令：")
        print("  对话 - 与附近的NPC对话")
        print("  战斗 - 进入战斗")
        print("  修炼 - 打坐修炼获得经验")
        print("  移动 <地点> - 前往新区域")
        print("  地图 - 查看当前区域信息")
        print("  任务 - 查看任务列表")
        print("  状态 - 查看当前状态")
        print("  背包 - 查看物品")
        print("  商店 - 打开商店")
        print("  保存 - 保存游戏进度")
        print("  新游戏 - 开始新游戏")
        print("  生成NPC - 随机生成一个NPC")
        print("  世界事件 - 触发世界动态事件")
        print("  查看NPC - 列出所有NPC")
        print("  帮助 - 显示此帮助信息")
        print("  退出 - 退出游戏")
        print("\n自由输入：")
        print("  你可以输入任何行动描述，例如：")
        print("  - 向东走")
        print("  - 观察周围")
        print("  - 搜索箱子")
        print("  - 询问村长关于村庄的事")
        print("\n战斗指令：")
        print("  攻击 - 普通攻击")
        print("  技能 <名称> - 使用技能")
        print("  防御 - 防御姿态")
        print("  丹药 - 使用丹药恢复")
        print("  逃跑 - 尝试逃跑")

    async def exit_game(self):
        print("\n正在保存游戏状态...")
        await self.engine.save_game()
        await self.engine.close()
        print("游戏已退出。感谢游玩！")
        self.running = False

    async def save_game(self):
        print("\n正在保存游戏进度...")
        await self.engine.save_game()

    async def new_game(self):
        print("\n确定要开始新游戏吗？当前进度将丢失。")
        confirm = input("输入 'yes' 确认，其他任意键取消：").strip().lower()

        if confirm in ["yes", "y", "是"]:
            print("\n正在开始新游戏...")
            await self.engine.close()

            self.engine = GameEngine()
            await self.engine.initialize()

            self.dialogue_manager = DialogueManager(
                self.engine.ai_service,
                self.engine.memory_manager,
                self.engine.narrator
            )

            await self._setup_initial_npcs()

            print("新游戏开始！")
            print("=" * 60)
            print("⚔️ 欢迎来到修仙世界")
            print("=" * 60)
            print()

            start_result = await self.engine.start_game()

            if start_result.get("narration"):
                print(start_result["narration"])
                print()

            state = start_result.get("world_state", {})
            print(f"📍 当前位置：{state.get('current_location')}")
            print(f"🕐 时间：{state.get('world_time')}")
            print(f"🌤 天气：{state.get('weather')}")
            print()
        else:
            print("已取消。")

    async def spawn_random_npc(self):
        print("\n正在生成随机NPC...")
        result = await self.engine.spawn_random_npc()

        if result.get("npc_name"):
            print(f"\n{result['message']}")
            print(f"👤 NPC姓名：{result['npc_name']}")
            print(f"📋 NPC类型：{result['npc_type']}")
        else:
            print("\nNPC生成失败。")

    async def spawn_special_npc(self):
        special_types = ["神秘旅行者", "传奇英雄", "古老智者", "魔法师", "商人王子"]

        print("\n可生成的特殊NPC类型：")
        for i, stype in enumerate(special_types, 1):
            print(f"  {i}. {stype}")

        choice = input("\n选择特殊NPC类型（输入序号）：").strip()

        try:
            index = int(choice) - 1
            if 0 <= index < len(special_types):
                special_type = special_types[index]
                print(f"\n正在生成{special_type}...")

                result = await self.engine.spawn_special_npc(special_type)

                if result.get("npc_name"):
                    print(f"\n{result['message']}")
                    print(f"👤 NPC姓名：{result['npc_name']}")
                    print(f"✨ 特殊类型：{result['special_type']}")
                else:
                    print("\n特殊NPC生成失败。")
            else:
                print("无效的选择。")
        except ValueError:
            print("请输入有效的数字。")

    async def trigger_world_event(self):
        print("\n正在触发世界动态事件...")
        result = await self.engine.trigger_dynamic_world()

        print(f"\n{result['message']}")

        for action in result.get("actions", []):
            action_type = action.get("type")
            data = action.get("data", {})

            if action_type == "npc_spawn":
                print(f"\n👤 [NPC出现] {data.get('message', '')}")
                if data.get("npc_name"):
                    print(f"  姓名：{data['npc_name']}")

            elif action_type == "event":
                print(f"\n🌍 [事件] {data.get('event', '')}")

            elif action_type == "weather_change":
                print(f"\n🌤 [天气变化] {data.get('message', '')}")

    async def list_npcs(self):
        all_npcs = self.engine.get_all_npcs()

        print("\n" + "=" * 40)
        print("👥 当前世界中的NPC")
        print("=" * 40)

        if all_npcs:
            for npc_id, npc in all_npcs.items():
                location = getattr(npc, 'location', '未知')
                role = getattr(npc, 'role', '村民')
                print(f"\n  [{npc_id}] {npc.name}")
                print(f"    📍 位置：{location}")
                print(f"    📋 角色：{role}")

            print(f"\n总计：{len(all_npcs)} 个NPC")
        else:
            print("\n当前世界中没有NPC。")


async def main():
    game = AIGameCLI()
    await game.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n游戏已中断。")
        sys.exit(0)
