"""Flask Web API 层 - 为修仙世界提供REST接口"""
import asyncio
import sys
import os
import json
import threading
from functools import wraps
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# 将项目根目录加入路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.game_engine import GameEngine, GameState

app = Flask(__name__, static_folder='static')
CORS(app)

# 全局游戏引擎实例
game_engine: GameEngine = None
loop: asyncio.AbstractEventLoop = None
init_lock = threading.Lock()
_last_save_mtime = 0


def run_async(coro):
    """在事件循环中运行异步函数"""
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=60)


def _check_save_reload():
    """检查存档文件是否被外部修改（如CLI端），如有则重新加载"""
    global game_engine, _last_save_mtime
    if game_engine is None:
        return
    save_file = game_engine.save_file
    if os.path.exists(save_file):
        mtime = os.path.getmtime(save_file)
        if _last_save_mtime > 0 and mtime > _last_save_mtime:
            # 存档被外部修改，重新加载状态
            try:
                game_engine.game_state = GameState.load(save_file)
                # 重新加载NPC
                npc_file = save_file.replace('.json', '_npcs.json')
                if os.path.exists(npc_file):
                    with open(npc_file, 'r', encoding='utf-8') as f:
                        npc_data = json.load(f)
                    # 合并NPC（保留内存中已有的）
                    for nid, data in npc_data.items():
                        if nid not in game_engine.npcs:
                            from agents.npc_agent import NPCAgent
                            npc = NPCAgent(
                                npc_id=data["npc_id"],
                                name=data["name"],
                                personality=data.get("personality", "友善"),
                                background=data.get("background", "无"),
                                goals=data.get("goals", ["生存"]),
                                ai_service=game_engine.ai_service,
                                memory_manager=game_engine.memory_manager,
                            )
                            npc.relationship_score = data.get("relationship_score", 0)
                            npc.role = data.get("role", "村民")
                            npc.location = data.get("location", "起始村庄")
                            npc.appearance = data.get("appearance", "")
                            npc.npc_type = data.get("npc_type", "commoner")
                            game_engine.npcs[nid] = npc
                            game_engine.world_simulator.npc_pool[nid] = npc
            except Exception as e:
                print(f"重新加载存档失败: {e}")
        _last_save_mtime = mtime


def ensure_engine():
    """确保游戏引擎已初始化"""
    global game_engine, loop, _last_save_mtime
    with init_lock:
        if game_engine is None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            game_engine = GameEngine()
            # 后台线程持续运行事件循环（修复：原来 run_until_complete 后循环停止，
            # 导致后续 run_coroutine_threadsafe 永远不执行，这是卡在"链接修仙世界"的根本原因）
            _loop_thread = threading.Thread(target=loop.run_forever, daemon=True)
            _loop_thread.start()
            # 通过线程安全的方式调度初始化协程
            init_future = asyncio.run_coroutine_threadsafe(
                game_engine.initialize(), loop
            )
            # 等待初始化完成（最多120秒，AI生成可能较慢）
            init_future.result(timeout=120)
            # 记录初始存档时间
            if os.path.exists(game_engine.save_file):
                _last_save_mtime = os.path.getmtime(game_engine.save_file)
    return game_engine


@app.route('/')
def index():
    return send_from_directory('static', 'index.html')


@app.route('/api/health', methods=['GET'])
def api_health():
    """健康检查"""
    status = {
        "status": "ok",
        "engine_initialized": game_engine is not None,
    }
    if game_engine:
        status["player"] = game_engine.game_state.player_name
        status["location"] = game_engine.game_state.current_location
        status["db_stats"] = game_engine.db.get_stats()
    return jsonify(status)


@app.route('/api/init', methods=['POST'])
def api_init():
    """初始化游戏"""
    engine = ensure_engine()
    try:
        result = run_async(engine.start_game())
        if "world_state" in result:
            map_info = engine.get_map_info()
            region = map_info.get("region", {})
            result["world_state"]["map_info"] = {
                "description": region.get("description", ""),
                "connections": region.get("connections", []),
                "danger_level": region.get("danger_level", 1),
                "all_regions": map_info.get("all_regions", {}),
            }

        # 后台异步生成AI内容（不阻塞响应）
        def _bg_generate():
            try:
                gen_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(gen_loop)
                gen_loop.run_until_complete(
                    engine.content_generator.ensure_content_availability(
                        realm_level=engine.game_state.cultivation.realm_index + 1,
                        context="游戏进程"
                    )
                )
                gen_loop.close()
            except Exception as e:
                print(f"后台内容生成跳过: {e}")

        import threading
        bg_thread = threading.Thread(target=_bg_generate, daemon=True)
        bg_thread.start()

        return jsonify({"success": True, **result})
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"初始化错误: {error_msg}")
        traceback.print_exc()
        return jsonify({"success": False, "error": f"初始化失败: {error_msg}"}), 500


@app.route('/api/state', methods=['GET'])
def api_state():
    """获取当前游戏状态"""
    engine = ensure_engine()
    _check_save_reload()
    map_info = engine.get_map_info()
    state_dict = engine.game_state.to_dict()
    # 将 map_info 嵌入 state 以便前端直接使用
    region = map_info.get("region", {})
    state_dict["map_info"] = {
        "description": region.get("description", ""),
        "connections": region.get("connections", []),
        "danger_level": region.get("danger_level", 1),
        "all_regions": map_info.get("all_regions", {}),
    }
    return jsonify({
        "success": True,
        "state": state_dict,
        "cultivation": engine.game_state.cultivation.to_dict(),
        "total_stats": engine.game_state.get_total_stats(),
        "map_info": map_info,
        "combat_status": engine.get_combat_status(),
    })


@app.route('/api/input', methods=['POST'])
def api_input():
    """处理玩家输入"""
    engine = ensure_engine()
    data = request.json
    player_input = data.get("input", "")
    input_type = data.get("type", "custom")

    if not player_input:
        return jsonify({"success": False, "error": "输入为空"}), 400

    try:
        result = run_async(engine.process_player_input(player_input, input_type))
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/move', methods=['POST'])
def api_move():
    """移动到指定位置"""
    engine = ensure_engine()
    data = request.json
    target = data.get("target", "")

    if not target:
        return jsonify({"success": False, "error": "未指定目标位置"}), 400

    try:
        result = run_async(engine.move_to_location(target))
        if "error" in result:
            return jsonify({"success": False, **result}), 400

        # 移动后后台生成新内容（敌人/物品），丰富游戏体验
        realm = engine.game_state.cultivation.realm_index + 1
        def _bg_move_content():
            try:
                gen_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(gen_loop)
                gen_loop.run_until_complete(
                    engine.content_generator.ensure_content_availability(
                        realm=realm,
                        context=f"玩家进入{target}"
                    )
                )
                gen_loop.close()
            except Exception as e:
                print(f"移动后内容生成跳过: {e}")
        bg_thread = threading.Thread(target=_bg_move_content, daemon=True)
        bg_thread.start()

        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/dialogue/start', methods=['POST'])
def api_dialogue_start():
    """开始与NPC对话"""
    engine = ensure_engine()
    data = request.json
    npc_id = data.get("npc_id", "")

    nearby = engine._get_nearby_npcs()
    if not nearby:
        return jsonify({"success": False, "error": "附近没有可以对话的NPC"}), 400

    # 如果指定了NPC ID则使用，否则选第一个
    target_id = npc_id if npc_id in nearby else nearby[0]
    npc = engine.npcs.get(target_id)

    if not npc:
        return jsonify({"success": False, "error": "找不到该NPC"}), 404

    try:
        context = engine._build_context()
        result = run_async(engine.dialogue_manager.start_dialogue(npc, context))
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/dialogue/continue', methods=['POST'])
def api_dialogue_continue():
    """继续对话"""
    engine = ensure_engine()
    data = request.json
    dialogue_id = data.get("dialogue_id", "")
    player_input = data.get("input", "")

    if not player_input:
        return jsonify({"success": False, "error": "输入为空"}), 400

    try:
        result = run_async(engine.dialogue_manager.continue_dialogue(dialogue_id, player_input))
        if "error" in result:
            return jsonify({"success": False, **result}), 400
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/dialogue/end', methods=['POST'])
def api_dialogue_end():
    """结束对话"""
    engine = ensure_engine()
    data = request.json
    dialogue_id = data.get("dialogue_id", "")

    ended = engine.dialogue_manager.end_dialogue(dialogue_id)
    return jsonify({"success": ended})


# ====== 战斗系统 API ======
@app.route('/api/combat/start', methods=['POST'])
def api_combat_start():
    """开始战斗"""
    engine = ensure_engine()
    data = request.json
    enemy_data = data.get("enemy", {})

    if not enemy_data:
        # 随机生成敌人
        region = engine.get_map_info()["region"]
        import random
        enemy_types = {1: ["妖兽"], 2: ["妖兽", "灵兽"], 3: ["灵兽", "魔修"],
                       4: ["魔修"], 5: ["灵兽"], 6: ["妖王"], 7: ["守护者"]}
        danger = region.get("danger_level", 1)
        possible = enemy_types.get(danger, ["妖兽"])
        enemy_type = random.choice(possible)
        entity = engine.combat_system.create_enemy(enemy_type, danger)
        enemy_data = entity.to_dict()

    result = engine.start_combat(enemy_data)
    return jsonify({"success": True, **result})


@app.route('/api/combat/action', methods=['POST'])
def api_combat_action():
    """执行战斗行动"""
    engine = ensure_engine()
    data = request.json
    action = data.get("action", "attack")
    skill = data.get("skill")

    if engine.get_combat_status() is None:
        return jsonify({"success": False, "error": "没有进行中的战斗"}), 400

    result = engine.execute_combat_turn(action, skill)

    if result.get("status") in ["victory", "defeat", "fled"]:
        engine.end_combat()

    return jsonify({"success": True, **result})


@app.route('/api/combat/status', methods=['GET'])
def api_combat_status():
    """获取战斗状态"""
    engine = ensure_engine()
    status = engine.get_combat_status()
    return jsonify({"success": True, "in_combat": status is not None, "combat": status})


# ====== 物品系统 API ======
@app.route('/api/inventory', methods=['GET'])
def api_inventory():
    """获取背包信息"""
    engine = ensure_engine()
    inventory_details = []
    for item_name in engine.game_state.inventory:
        info = engine.item_system.get_item_info(item_name)
        inventory_details.append({
            "name": item_name,
            "description": info.get("description", "") if info else "",
            "type": info.get("type", "") if info else "",
            "rarity": info.get("rarity", "common") if info else "common",
            "rarity_name": engine.item_system.get_item_rarity_name(item_name),
            "color": engine.item_system.get_item_color(item_name),
        })

    return jsonify({
        "success": True,
        "inventory": inventory_details,
        "equipment": engine.game_state.equipment,
    })


@app.route('/api/inventory/use', methods=['POST'])
def api_use_item():
    """使用物品"""
    engine = ensure_engine()
    data = request.json
    item_name = data.get("item", "")

    result = engine.use_item(item_name)
    if "error" in result:
        return jsonify({"success": False, **result}), 400
    return jsonify({"success": True, **result})


@app.route('/api/shop', methods=['GET'])
def api_shop():
    """获取商店物品"""
    engine = ensure_engine()
    items = engine.get_shop_items()
    for item in items:
        item["color"] = engine.item_system.get_item_color(item["name"])
        item["rarity_name"] = engine.item_system.get_item_rarity_name(item["name"])
    return jsonify({"success": True, "items": items, "gold": engine.game_state.stats["gold"]})


@app.route('/api/shop/buy', methods=['POST'])
def api_buy():
    """购买物品"""
    engine = ensure_engine()
    data = request.json
    item_name = data.get("item", "")

    result = engine.buy_item(item_name)
    if "error" in result:
        return jsonify({"success": False, **result}), 400
    return jsonify({"success": True, **result})


@app.route('/api/shop/sell', methods=['POST'])
def api_sell():
    """出售物品"""
    engine = ensure_engine()
    data = request.json
    item_name = data.get("item", "")

    result = engine.sell_item(item_name)
    if "error" in result:
        return jsonify({"success": False, **result}), 400
    return jsonify({"success": True, **result})


# ====== 修仙系统 API ======
@app.route('/api/cultivation', methods=['GET'])
def api_cultivation():
    """获取修仙信息"""
    engine = ensure_engine()
    info = engine.get_cultivation_info()
    return jsonify({"success": True, **info})


@app.route('/api/cultivation/meditate', methods=['POST'])
def api_meditate():
    """打坐修炼"""
    engine = ensure_engine()
    try:
        result = run_async(engine.meditate())
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/cultivation/learn', methods=['POST'])
def api_learn_skill():
    """学习技能"""
    engine = ensure_engine()
    data = request.json
    skill_name = data.get("skill", "")

    if engine.game_state.cultivation.can_learn_skill(skill_name):
        engine.game_state.cultivation.learn_skill(skill_name)
        return jsonify({"success": True, "skill": skill_name, "message": f"学会了 {skill_name}！"})
    else:
        return jsonify({"success": False, "error": f"无法学习 {skill_name}（已学会或境界不足）"}), 400


# ====== NPC 系统 API ======
@app.route('/api/npcs', methods=['GET'])
def api_npcs():
    """获取所有NPC列表"""
    engine = ensure_engine()
    all_npcs = engine.get_all_npcs()
    npc_list = []
    for npc_id, npc in all_npcs.items():
        npc_list.append({
            "id": npc_id,
            "name": npc.name,
            "location": getattr(npc, 'location', '未知'),
            "role": getattr(npc, 'role', '村民'),
            "personality": npc.personality,
            "relationship": npc.relationship_score,
        })
    return jsonify({"success": True, "npcs": npc_list})


@app.route('/api/npcs/spawn', methods=['POST'])
def api_spawn_npc():
    """生成NPC"""
    engine = ensure_engine()
    data = request.json or {}
    npc_type = data.get("type", "commoner")
    special = data.get("special")

    try:
        if special:
            result = run_async(engine.spawn_special_npc(special))
        else:
            result = run_async(engine.spawn_random_npc(npc_type))
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ====== 任务系统 API ======
@app.route('/api/quests', methods=['GET'])
def api_quests():
    """获取任务列表"""
    engine = ensure_engine()
    try:
        result = run_async(engine.get_quests())
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ====== 世界系统 API ======
@app.route('/api/world/event', methods=['POST'])
def api_world_event():
    """触发世界事件"""
    engine = ensure_engine()
    try:
        result = run_async(engine.trigger_dynamic_world())
        return jsonify({"success": True, **result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ====== 内容生成 API ======
@app.route('/api/content/generate', methods=['POST'])
def api_generate_content():
    """按需生成游戏内容（物品/敌人/技能/区域）"""
    engine = ensure_engine()
    data = request.json or {}
    gen_type = data.get("type", "auto")  # auto/item/enemy/skill/region
    realm = engine.game_state.cultivation.realm_index + 1
    context = data.get("context", "")

    def _bg_gen():
        try:
            gen_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(gen_loop)
            if gen_type == "auto" or gen_type == "all":
                gen_loop.run_until_complete(
                    engine.content_generator.ensure_content_availability(realm, context)
                )
            elif gen_type == "item":
                item_type = data.get("item_type", "consumable")
                gen_loop.run_until_complete(
                    engine.content_generator.generate_item(item_type, realm, context)
                )
            elif gen_type == "enemy":
                enemy_type = data.get("enemy_type", "")
                gen_loop.run_until_complete(
                    engine.content_generator.generate_enemy_template(enemy_type, realm, context)
                )
            elif gen_type == "skill":
                skill_type = data.get("skill_type", "attack")
                gen_loop.run_until_complete(
                    engine.content_generator.generate_skill(realm, skill_type, context)
                )
            elif gen_type == "region":
                gen_loop.run_until_complete(
                    engine.content_generator.generate_region(
                        connect_to=data.get("connect_to", ""),
                        danger_range=(max(1, realm - 1), min(7, realm + 1)),
                        context=context
                    )
                )
            gen_loop.close()
        except Exception as e:
            print(f"后台内容生成失败: {e}")

    bg_thread = threading.Thread(target=_bg_gen, daemon=True)
    bg_thread.start()

    return jsonify({"success": True, "message": f"正在后台生成 {gen_type} 类型内容...", "stats": engine.db.get_stats()})


@app.route('/api/content/stats', methods=['GET'])
def api_content_stats():
    """获取内容库统计"""
    engine = ensure_engine()
    return jsonify({"success": True, "stats": engine.db.get_stats()})


# ====== 存档系统 API ======
@app.route('/api/save', methods=['POST'])
def api_save():
    """保存游戏"""
    global _last_save_mtime
    engine = ensure_engine()
    try:
        run_async(engine.save_game())
        # 更新mtime记录
        if os.path.exists(engine.save_file):
            _last_save_mtime = os.path.getmtime(engine.save_file)
        return jsonify({"success": True, "message": "游戏已保存"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/reload', methods=['POST'])
def api_reload():
    """从磁盘重新加载存档（CLI同步用）"""
    engine = ensure_engine()
    try:
        if os.path.exists(engine.save_file):
            engine.game_state = GameState.load(engine.save_file)
            global _last_save_mtime
            _last_save_mtime = os.path.getmtime(engine.save_file)
            return jsonify({"success": True, "message": "存档已重新加载"})
        return jsonify({"success": False, "error": "没有找到存档"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/save/load', methods=['POST'])
def api_load():
    """加载存档"""
    engine = ensure_engine()
    try:
        run_async(engine.load_game())
        return jsonify({"success": True, "state": engine.game_state.to_dict()})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def main():
    print("=" * 50)
    print("  修仙世界 - Web服务器启动中...")
    print("=" * 50)
    print()
    ensure_engine()
    print()
    print("✅ 游戏引擎初始化完成")
    print("🌐 请访问 http://localhost:5000")
    print()
    app.run(host='0.0.0.0', port=5000, debug=False)


if __name__ == '__main__':
    main()
