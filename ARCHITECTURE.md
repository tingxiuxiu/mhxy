# 文字西游 - 系统架构设计文档

**版本**: v1.0.0  
**日期**: 2026-08-20  
**状态**: 待评审

---

## 1. 系统架构总览

### 1.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                         客户端层 (Clients)                           │
├─────────────────────┬─────────────────────┬─────────────────────────┤
│  文字游戏客户端     │   运营管理后台      │   二期UI客户端(预留)    │
│  (React+TS)        │   (React+TS)        │   (Unity/Cocos)         │
└─────────┬───────────┴──────────┬──────────┴───────────┬─────────────┘
          │                      │                      │
          │  REST API           │  REST API            │  REST API + WS
          │  + WebSocket        │                      │
┌─────────▼──────────────────────▼──────────────────────▼─────────────┐
│                        Nginx (反向代理/负载均衡)                     │
│              /api/* → 后端   /ws → WebSocket   /admin → 后台         │
└─────────┬────────────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────────────┐
│                      FastAPI 应用层 (Backend)                        │
├─────────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐            │
│  │  API路由  │  │ WebSocket│  │  权限认证 │  │  限流中间件│           │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘            │
│       │             │             │             │                   │
│  ┌────▼─────────────▼─────────────▼─────────────▼─────┐            │
│  │                  业务服务层 (Services)              │            │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │            │
│  │  │角色服│ │战斗服│ │地图服│ │物品服│ │任务服│    │            │
│  │  │务    │ │务    │ │务    │ │务    │ │务    │    │            │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘    │            │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐    │            │
│  │  │社交服│ │经济服│ │帮派服│ │宠物服│ │聊天服│    │            │
│  │  │务    │ │务    │ │务    │ │务    │ │务    │    │            │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘    │            │
│  └──────────────────────┬────────────────────────────┘            │
│                         │                                           │
│  ┌──────────────────────▼────────────────────────────┐            │
│  │                  数据访问层 (DAL)                   │            │
│  │    SQLAlchemy (ORM)    │    Redis 客户端封装       │            │
│  └──────────┬─────────────┴────────────┬──────────────┘            │
└─────────────┼──────────────────────────┼───────────────────────────┘
              │                          │
┌─────────────▼──────────┐    ┌──────────▼───────────┐
│    PostgreSQL 数据库   │    │      Redis 缓存       │
│  (持久化存储)          │    │  (会话/缓存/消息/状态)│
│  - 玩家/角色数据       │    │  - 在线状态          │
│  - 物品/装备数据       │    │  - 战斗房间          │
│  - 帮派/社交数据       │    │  - 聊天频道          │
│  - 游戏配置数据        │    │  - 分布式锁          │
│  - 操作日志            │    │  - 计数器(限流)      │
└────────────────────────┘    └───────────────────────┘
```

### 1.2 设计原则

1. **服务端权威**: 所有数值计算、状态判定、随机数生成在服务端完成
2. **分层架构**: API → Service → DAL 三层清晰分离，每层只依赖下层
3. **无状态设计**: API服务无状态，会话/状态存储在Redis，支持水平扩展
4. **异步优先**: 数据库/Redis全部使用异步驱动，高并发下性能优异
5. **配置驱动**: 游戏数值、物品、技能、怪物等全部通过配置管理，不改代码即可调整
6. **可测试性**: 核心逻辑纯函数化，依赖注入，便于单元测试和Mock

---

## 2. 目录结构设计

```
/workspace
├── backend/                    # FastAPI后端
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py            # FastAPI入口
│   │   ├── config.py          # 配置管理(pydantic-settings)
│   │   ├── database.py        # 数据库连接/Session
│   │   ├── redis_client.py    # Redis连接/封装
│   │   ├── dependencies.py    # 依赖注入(get_db/get_current_user等)
│   │   ├── exceptions.py      # 自定义异常
│   │   ├── middleware/         # 中间件
│   │   │   ├── __init__.py
│   │   │   ├── auth.py        # 认证中间件
│   │   │   ├── rate_limit.py  # 限流中间件
│   │   │   └── error_handler.py # 全局异常处理
│   │   ├── models/            # SQLAlchemy模型
│   │   │   ├── __init__.py
│   │   │   ├── user.py        # 用户/账号模型
│   │   │   ├── character.py   # 角色/属性模型
│   │   │   ├── item.py        # 物品/装备/背包模型
│   │   │   ├── pet.py         # 宠物模型
│   │   │   ├── battle.py      # 战斗相关模型(日志等)
│   │   │   ├── map.py         # 地图/场景/NPC模型
│   │   │   ├── quest.py       # 任务模型
│   │   │   ├── social.py      # 好友/组队/聊天模型
│   │   │   ├── guild.py       # 帮派模型
│   │   │   ├── economy.py     # 交易/摆摊/商城/充值模型
│   │   │   └── config.py      # 游戏配置模型(动态配置)
│   │   ├── schemas/           # Pydantic模型(请求/响应)
│   │   │   ├── __init__.py
│   │   │   ├── common.py      # 通用响应模型
│   │   │   ├── user.py
│   │   │   ├── character.py
│   │   │   ├── battle.py
│   │   │   ├── item.py
│   │   │   ├── quest.py
│   │   │   ├── social.py
│   │   │   └── admin.py       # 管理后台专用
│   │   ├── services/          # 核心业务逻辑
│   │   │   ├── __init__.py
│   │   │   ├── user_service.py
│   │   │   ├── character_service.py
│   │   │   ├── battle_service.py      # 战斗核心引擎
│   │   │   ├── battle_state.py        # 战斗状态机
│   │   │   ├── map_service.py
│   │   │   ├── npc_service.py
│   │   │   ├── item_service.py
│   │   │   ├── pet_service.py
│   │   │   ├── quest_service.py
│   │   │   ├── quest_shimen.py        # 师门任务逻辑
│   │   │   ├── quest_zhuagui.py       # 抓鬼任务逻辑
│   │   │   ├── quest_hubiao.py        # 护镖任务逻辑
│   │   │   ├── quest_dungeon.py       # 副本任务逻辑
│   │   │   ├── social_service.py
│   │   │   ├── chat_service.py
│   │   │   ├── guild_service.py
│   │   │   ├── economy_service.py
│   │   │   ├── trade_service.py
│   │   │   ├── shop_service.py
│   │   │   └── admin_service.py
│   │   ├── api/               # API路由
│   │   │   ├── __init__.py   # 路由聚合
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── character.py
│   │   │   │   ├── map.py
│   │   │   │   ├── battle.py
│   │   │   │   ├── item.py
│   │   │   │   ├── pet.py
│   │   │   │   ├── quest.py
│   │   │   │   ├── social.py
│   │   │   │   ├── guild.py
│   │   │   │   ├── economy.py
│   │   │   │   └── ws.py     # WebSocket入口
│   │   │   └── admin/        # 管理后台API
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── config.py
│   │   │       ├── user.py
│   │   │       └── stats.py
│   │   ├── game/              # 游戏核心数据(静态配置)
│   │   │   ├── __init__.py
│   │   │   ├── constants.py   # 游戏常量
│   │   │   ├── enums.py       # 枚举定义
│   │   │   ├── formulas.py    # 计算公式(伤害/经验/命中)
│   │   │   └── initial_data/  # 初始化配置JSON
│   │   │       ├── maps.json
│   │   │       ├── npcs.json
│   │   │       ├── items.json
│   │   │       ├── skills.json
│   │   │       ├── monsters.json
│   │   │       └── quests.json
│   │   └── utils/             # 工具函数
│   │       ├── __init__.py
│   │       ├── security.py    # 密码加密/JWT
│   │       ├── ratelimit.py   # 限流工具
│   │       ├── sensitive.py   # 敏感词过滤
│   │       └── id_gen.py      # ID生成器(雪花算法)
│   ├── tests/                 # 后端测试
│   │   ├── __init__.py
│   │   ├── conftest.py        # pytest fixtures
│   │   ├── unit/              # 单元测试
│   │   │   ├── test_battle_engine.py
│   │   │   ├── test_formulas.py
│   │   │   ├── test_quest_logic.py
│   │   │   └── test_services.py
│   │   ├── integration/       # 集成测试
│   │   │   ├── test_auth_api.py
│   │   │   ├── test_character_api.py
│   │   │   └── test_battle_flow.py
│   │   └── e2e/               # 端到端测试
│   │       └── test_full_game_flow.py
│   ├── alembic/               # 数据库迁移
│   │   ├── versions/
│   │   └── env.py
│   ├── pyproject.toml         # 依赖管理(poetry/pip)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
├── frontend/                  # 游戏文字客户端(React)
│   ├── src/
│   │   ├── components/        # UI组件
│   │   ├── pages/             # 页面
│   │   ├── hooks/             # 自定义Hooks
│   │   ├── services/          # API/WebSocket服务
│   │   ├── store/             # 状态管理(Redux/Zustand)
│   │   ├── utils/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
│
├── admin/                     # 运营管理后台(React)
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── store/
│   └── package.json
│
├── docker-compose.yml         # 一键启动所有服务
├── Makefile                   # 常用命令
└── README.md
```

---

## 3. 数据库设计

### 3.1 ER图概览

```
User (1) ──── (N) Character
Character (1) ── (1) CharacterStats
Character (1) ── (N) CharacterItem (背包)
Character (1) ── (N) CharacterPet
Character (1) ── (N) CharacterQuest
Character (N) ── (N) Friend (Character)
Character (N) ── (1) Team
Character (N) ── (1) GuildMember ── (1) Guild
Battle (1) ── (N) BattleParticipant
Battle (1) ── (N) BattleLog
Config 系列表 (MapConfig/NpcConfig/ItemConfig/SkillConfig/MonsterConfig)
```

### 3.2 核心表结构设计

#### 3.2.1 用户与角色

**users 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 主键(雪花ID) |
| username | VARCHAR(32) UNIQUE | 用户名 |
| password_hash | VARCHAR(128) | bcrypt加密密码 |
| email | VARCHAR(128) | 邮箱(可选) |
| is_active | BOOLEAN | 是否启用 |
| is_admin | BOOLEAN | 是否管理员 |
| last_login_at | TIMESTAMP | 最后登录时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**characters 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 角色ID |
| user_id | BIGINT FK | 所属用户 |
| name | VARCHAR(16) UNIQUE | 角色名 |
| gender | SMALLINT | 性别 1男 2女 |
| race | SMALLINT | 种族 1人 2仙 3魔 |
| faction | SMALLINT | 门派 1大唐 2化生 3龙宫 4普陀 5狮驼 6盘丝 |
| level | INTEGER | 等级 1-175 |
| exp | BIGINT | 当前经验 |
| map_id | INTEGER FK | 当前所在地图 |
| pos_x | INTEGER | X坐标 |
| pos_y | INTEGER | Y坐标 |
| team_id | BIGINT FK | 队伍ID(可选) |
| guild_id | BIGINT FK | 帮派ID(可选) |
| cash | BIGINT | 现金 |
| reserve_cash | BIGINT | 储备金 |
| jade | BIGINT | 仙玉 |
| hp | INTEGER | 当前气血 |
| mp | INTEGER | 当前魔法 |
| anger | INTEGER | 当前愤怒值 |
| is_online | BOOLEAN | 是否在线 |
| last_logout_at | TIMESTAMP | 最后下线时间 |
| created_at | TIMESTAMP | 创建时间 |
| updated_at | TIMESTAMP | 更新时间 |

**character_stats 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| character_id | BIGINT PK FK | 角色ID |
| base_hp | INTEGER | 基础气血 |
| base_mp | INTEGER | 基础魔法 |
| base_hit | INTEGER | 命中 |
| base_damage | INTEGER | 伤害 |
| base_defense | INTEGER | 防御 |
| base_speed | INTEGER | 速度 |
| base_magic_damage | INTEGER | 法伤 |
| base_magic_defense | INTEGER | 法防 |
| pot_points | INTEGER | 剩余潜力点 |
| pot_tizhi | INTEGER | 体质加点 |
| pot_moli | INTEGER | 魔力加点 |
| pot_liliang | INTEGER | 力量加点 |
| pot_naili | INTEGER | 耐力加点 |
| pot_minjie | INTEGER | 敏捷加点 |
| practice_phys | INTEGER | 攻法修炼 |
| practice_def | INTEGER | 物防修炼 |
| practice_mdef | INTEGER | 法防修炼 |
| practice_capture | INTEGER | 猎术修炼 |
| updated_at | TIMESTAMP | 更新时间 |

#### 3.2.2 物品与背包

**item_configs 表 (配置表，管理后台维护)**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 物品ID |
| name | VARCHAR(32) | 物品名称 |
| type | SMALLINT | 类型 1装备 2药品 3烹饪 4暗器 5杂物 6任务物品 |
| subtype | SMALLINT | 子类型(装备部位等) |
| level_req | INTEGER | 携带等级要求 |
| race_req | SMALLINT | 种族限制(0不限) |
| faction_req | SMALLINT | 门派限制(0不限) |
| stackable | BOOLEAN | 是否可堆叠 |
| max_stack | INTEGER | 最大堆叠数 |
| sell_price | INTEGER | 卖店价格 |
| buy_price | INTEGER | 商店价格(0=不卖) |
| effect | JSONB | 效果(药品:加血/加蓝;装备:属性加成) |
| resource_id | VARCHAR(64) | 美术资源ID(二期用) |
| description | TEXT | 物品描述 |
| is_active | BOOLEAN | 是否生效 |
| version | INTEGER | 配置版本号 |

**character_items 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 实例ID |
| character_id | BIGINT FK | 角色ID |
| item_config_id | INTEGER FK | 物品配置ID |
| slot_type | SMALLINT | 位置类型 1背包 2装备 3仓库 4宠物装备 |
| slot_index | INTEGER | 格子序号 |
| quantity | INTEGER | 数量(堆叠) |
| bind_type | SMALLINT | 绑定类型 0未绑 1装备绑 2拾取绑 |
| extra_attr | JSONB | 额外属性(装备附加属性/耐久等) |
| created_at | TIMESTAMP | 获得时间 |

#### 3.2.3 宠物

**pet_configs 表 (配置表)**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 宠物种类ID |
| name | VARCHAR(32) | 名称 |
| level_req | INTEGER | 携带等级 |
| base_hp | INTEGER | 基础气血资质 |
| base_mp | INTEGER | 基础魔法资质 |
| base_attack | INTEGER | 攻击资质 |
| base_defense | INTEGER | 防御资质 |
| base_speed | INTEGER | 速度资质 |
| base_magic | INTEGER | 法力资质 |
| growth_rate | NUMERIC(4,3) | 成长率 |
| possible_skills | JSONB | 可能携带技能列表 |
| capture_rate | INTEGER | 捕捉成功率(0-100) |
| resource_id | VARCHAR(64) | 美术资源ID |

**character_pets 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 宠物实例ID |
| character_id | BIGINT FK | 主人ID |
| pet_config_id | INTEGER FK | 宠物种类ID |
| nickname | VARCHAR(32) | 昵称 |
| level | INTEGER | 等级 |
| exp | BIGINT | 经验 |
| hp | INTEGER | 当前气血 |
| mp | INTEGER | 当前魔法 |
| loyalty | INTEGER | 忠诚度 |
| life | INTEGER | 寿命 |
| is_battle | BOOLEAN | 是否出战中 |
| slot_index | INTEGER | 宠物栏位(0-3出战位，4-7备用) |
| skills | JSONB | 已学技能列表 |
| attr_gz | INTEGER | 攻击资质(实际) |
| attr_fy | INTEGER | 防御资质(实际) |
| attr_tz | INTEGER | 体力资质(实际) |
| attr_fz | INTEGER | 法力资质(实际) |
| attr_sd | INTEGER | 速度资质(实际) |
| growth | NUMERIC(4,3) | 实际成长率 |
| created_at | TIMESTAMP | 获得时间 |

#### 3.2.4 战斗相关

**battles 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 战斗ID |
| battle_type | SMALLINT | 类型 1野外 2抓鬼 3任务 4副本 5PK |
| map_id | INTEGER FK | 所在地图 |
| status | SMALLINT | 状态 1进行中 2胜利 3失败 4逃跑 5超时 |
| turn | INTEGER | 当前回合 |
| started_at | TIMESTAMP | 开始时间 |
| ended_at | TIMESTAMP | 结束时间 |
| extra_data | JSONB | 扩展数据(副本ID/任务ID等) |

**battle_participants 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 参战者ID |
| battle_id | BIGINT FK | 战斗ID |
| side | SMALLINT | 阵营 1我方 2敌方 |
| char_type | SMALLINT | 类型 1玩家 2宠物 3怪物 |
| char_id | BIGINT | 对应玩家/宠物/怪物配置ID |
| char_name | VARCHAR(32) | 名称快照 |
| hp | INTEGER | 战斗中气血 |
| mp | INTEGER | 战斗中魔法 |
| hp_max | INTEGER | 最大气血 |
| mp_max | INTEGER | 最大魔法 |
| damage | INTEGER | 伤害 |
| defense | INTEGER | 防御 |
| speed | INTEGER | 速度 |
| position | INTEGER | 站位(1-5) |
| is_dead | BOOLEAN | 是否死亡 |
| buffs | JSONB | 增益/减益状态 |

**battle_logs 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 日志ID |
| battle_id | BIGINT FK | 战斗ID |
| turn | INTEGER | 回合 |
| actor_id | BIGINT FK | 行动者(参战者ID) |
| action_type | SMALLINT | 行动类型 1普攻 2法术 3道具 4防御 5召唤 6逃跑 7捕捉 |
| action_targets | JSONB | 目标列表 |
| action_data | JSONB | 行动详情(伤害数值/技能ID/治疗量等) |
| created_at | TIMESTAMP | 时间 |

#### 3.2.5 地图与NPC

**map_configs 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 地图ID |
| name | VARCHAR(32) | 地图名称 |
| type | SMALLINT | 类型 1城市 2野外 3门派 4副本 5特殊 |
| width | INTEGER | 宽度(格子数) |
| height | INTEGER | 高度(格子数) |
| adjacent_maps | JSONB | 相邻地图列表 [{map_id, entry_x, entry_y}] |
| is_dark | BOOLEAN | 是否暗雷遇敌 |
| encounter_rate | INTEGER | 遇敌概率(0-1000，千分比) |
| encounters | JSONB | 遇敌配置 [{monster_id, weight, min_level, max_level}] |
| resource_id | VARCHAR(64) | 地图资源ID |

**npc_configs 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | NPC ID |
| name | VARCHAR(32) | NPC名称 |
| title | VARCHAR(32) | 称号 |
| map_id | INTEGER FK | 所在地图 |
| pos_x | INTEGER | X坐标 |
| pos_y | INTEGER | Y坐标 |
| npc_type | SMALLINT | 类型 1普通 2商店 3任务 4传送 5功能 |
| dialog | TEXT | 默认对话 |
| shop_items | JSONB | 商店售卖物品 [{item_id, price}] |
| quest_ids | JSONB | 可接任务ID列表 |
| teleport_to | JSONB | 传送目标 {map_id, x, y} |
| functions | JSONB | 功能列表 |
| resource_id | VARCHAR(64) | 形象资源ID |

#### 3.2.6 技能与怪物

**skill_configs 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 技能ID |
| name | VARCHAR(32) | 技能名称 |
| type | SMALLINT | 类型 1门派法术 2特技 3特效 4宠物技能 |
| faction | SMALLINT | 所属门派(0通用) |
| mp_cost | INTEGER | 魔法消耗 |
| anger_cost | INTEGER | 愤怒消耗 |
| target_type | SMALLINT | 目标类型 1敌单 2敌多 3己单 4己多 5己方全体 6敌方全体 |
| target_count | INTEGER | 目标数量 |
| effect_type | SMALLINT | 效果类型 1物理伤害 2法术伤害 3治疗 4增益 5减益 6封印 |
| effect_value | JSONB | 效果参数(伤害公式系数/治疗量/持续回合等) |
| cooldown | INTEGER | 冷却回合 |
| level_req | INTEGER | 学习等级要求 |
| description | TEXT | 技能描述 |
| resource_id | VARCHAR(64) | 特效资源ID |

**monster_configs 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 怪物ID |
| name | VARCHAR(32) | 名称 |
| level | INTEGER | 等级 |
| hp | INTEGER | 气血 |
| mp | INTEGER | 魔法 |
| damage | INTEGER | 伤害 |
| defense | INTEGER | 防御 |
| speed | INTEGER | 速度 |
| magic_damage | INTEGER | 法伤 |
| magic_defense | INTEGER | 法防 |
| skills | JSONB | 使用技能列表 [{skill_id, weight}] |
| exp_reward | INTEGER | 经验奖励 |
| cash_reward | INTEGER | 金钱奖励 |
| drop_items | JSONB | 掉落表 [{item_id, rate, min_count, max_count}] |
| is_boss | BOOLEAN | 是否BOSS |
| resource_id | VARCHAR(64) | 怪物形象ID |

#### 3.2.7 任务系统

**quest_configs 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 任务ID |
| name | VARCHAR(64) | 任务名称 |
| type | SMALLINT | 类型 1新手 2师门 3抓鬼 4护镖 5剧情 6副本 |
| level_min | INTEGER | 最低等级 |
| level_max | INTEGER | 最高等级(0无限制) |
| repeatable | BOOLEAN | 是否可重复 |
| daily_limit | INTEGER | 每日次数限制(0无限制) |
| giver_npc_id | INTEGER FK | 接取NPC |
| steps | JSONB | 任务步骤配置(复杂结构，见下方) |
| rewards | JSONB | 奖励配置(exp, cash, items) |
| description | TEXT | 任务描述 |

**character_quests 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 记录ID |
| character_id | BIGINT FK | 角色ID |
| quest_id | INTEGER FK | 任务ID |
| status | SMALLINT | 状态 1进行中 2可完成 3已完成 4放弃 5失败 |
| current_step | INTEGER | 当前步骤序号 |
| step_data | JSONB | 步骤进度数据 |
| accepted_at | TIMESTAMP | 接取时间 |
| completed_at | TIMESTAMP | 完成时间 |
| times_completed | INTEGER | 完成次数(日常任务用) |
| today_date | DATE | 日期(日常任务重置用) |

#### 3.2.8 社交与帮派

**friends 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | ID |
| char_id | BIGINT FK | 角色ID |
| friend_id | BIGINT FK | 好友角色ID |
| intimacy | INTEGER | 友好度 |
| group_name | VARCHAR(32) | 分组名 |
| is_blacklist | BOOLEAN | 是否黑名单 |
| created_at | TIMESTAMP | 添加时间 |

**teams 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 队伍ID |
| leader_id | BIGINT FK | 队长ID |
| target | VARCHAR(64) | 队伍目标 |
| is_locked | BOOLEAN | 是否锁定(禁止加入) |
| created_at | TIMESTAMP | 创建时间 |

**guilds 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 帮派ID |
| name | VARCHAR(16) UNIQUE | 帮派名称 |
| leader_id | BIGINT FK | 帮主ID |
| level | INTEGER | 帮派等级 |
| funds | BIGINT | 帮派资金 |
| prosperity | INTEGER | 繁荣度 |
| announcement | TEXT | 帮派公告 |
| max_members | INTEGER | 最大人数 |
| created_at | TIMESTAMP | 创建时间 |

**guild_members 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | ID |
| guild_id | BIGINT FK | 帮派ID |
| character_id | BIGINT FK | 角色ID |
| position | SMALLINT | 职位 1帮主 2副帮主 3长老 4堂主 5精英 6帮众 |
| contribution | INTEGER | 帮贡(累计) |
| current_contrib | INTEGER | 当前可用帮贡 |
| joined_at | TIMESTAMP | 加入时间 |

**guild_skills 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | ID |
| guild_id | BIGINT FK | 帮派ID |
| skill_id | INTEGER FK | 技能ID(强身/冥想等辅助技能) |
| level | INTEGER | 技能等级 |

#### 3.2.9 经济交易

**trades 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 交易ID |
| initiator_id | BIGINT FK | 发起方 |
| target_id | BIGINT FK | 目标方 |
| status | SMALLINT | 状态 1请求中 2对方同意 3已确认 4已完成 5已取消 |
| initiator_cash | BIGINT | 发起方放的现金 |
| target_cash | BIGINT | 目标方放的现金 |
| initiator_items | JSONB | 发起方放的物品列表 |
| target_items | JSONB | 目标方放的物品列表 |
| created_at | TIMESTAMP | 创建时间 |
| completed_at | TIMESTAMP | 完成时间 |

**stalls 表 (摆摊)**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 摊位ID |
| owner_id | BIGINT FK | 摊主ID |
| title | VARCHAR(32) | 摊位名称 |
| map_id | INTEGER FK | 所在地图 |
| pos_x | INTEGER | X坐标 |
| pos_y | INTEGER | Y坐标 |
| is_open | BOOLEAN | 是否开张 |
| created_at | TIMESTAMP | 摆摊时间 |

**stall_items 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | ID |
| stall_id | BIGINT FK | 摊位ID |
| char_item_id | BIGINT FK | 物品实例ID |
| price | BIGINT | 单价(现金) |
| sold | BOOLEAN | 是否已售 |

**recharge_orders 表**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | 订单ID |
| user_id | BIGINT FK | 用户ID |
| order_no | VARCHAR(64) UNIQUE | 订单号 |
| amount | INTEGER | 金额(分) |
| jade_amount | INTEGER | 仙玉数量 |
| pay_channel | VARCHAR(32) | 支付渠道(wx/alipay) |
| status | SMALLINT | 状态 1待支付 2已支付 3已发货 4失败 5退款 |
| paid_at | TIMESTAMP | 支付时间 |
| created_at | TIMESTAMP | 创建时间 |

**chat_logs 表 (聊天记录，主要放Redis，持久化摘要)**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | ID |
| channel | SMALLINT | 频道 |
| speaker_id | BIGINT | 发言者ID |
| speaker_name | VARCHAR(32) | 发言者名称 |
| content | VARCHAR(512) | 内容 |
| created_at | TIMESTAMP | 时间 |

**admin_users 表 (管理员)**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER PK | 管理员ID |
| username | VARCHAR(32) UNIQUE | 用户名 |
| password_hash | VARCHAR(128) | 密码 |
| role | SMALLINT | 角色 1超级管理员 2GM 3运营 |
| is_active | BOOLEAN | 是否启用 |
| last_login_at | TIMESTAMP | 最后登录 |
| created_at | TIMESTAMP | 创建时间 |

**operation_logs 表 (操作审计日志)**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | ID |
| char_id | BIGINT | 操作角色ID(0为系统) |
| action | VARCHAR(64) | 操作类型: item_gain/item_lose/cash_add/cash_cost/jade_add/jade_cost/trade/stall_buy/recharge/gm_operate |
| detail | JSONB | 详细信息: 变动前数量、变动后数量、原因、关联ID |
| ip | VARCHAR(45) | IP地址 |
| created_at | TIMESTAMP | 操作时间 |

**banned_users 表 (封禁记录)**
| 字段 | 类型 | 说明 |
|------|------|------|
| id | BIGINT PK | ID |
| user_id | BIGINT FK | 用户ID |
| char_id | BIGINT FK | 角色ID(可选) |
| reason | VARCHAR(256) | 封禁原因 |
| ban_type | SMALLINT | 类型 1临时封禁 2永久封禁 3禁言 |
| ban_until | TIMESTAMP | 解封时间(永久封禁为NULL) |
| operator_id | BIGINT | 操作管理员ID |
| created_at | TIMESTAMP | 封禁时间 |
| is_revoked | BOOLEAN | 是否已解封 |
| revoked_at | TIMESTAMP | 解封时间 |

---

## 4. Redis 数据结构设计

### 4.1 Key命名规范
- 前缀: `wx:` (文字西游简称)
- 格式: `wx:{业务}:{标识}:{参数}`

### 4.2 核心Key设计

| Key | 类型 | 说明 | TTL |
|-----|------|------|-----|
| `wx:online:char:{char_id}` | STRING | 角色在线状态，值为WS连接ID | - (断线删除) |
| `wx:online:count` | STRING | 当前在线人数统计 | - |
| `wx:ws:conn:{conn_id}` | HASH | WebSocket连接信息: char_id, ip, connect_time | 24h |
| `wx:char:state:{char_id}` | HASH | 角色当前状态快照: map_id, x, y, hp, mp, team_id, guild_id | - (心跳更新) |
| `wx:battle:{battle_id}` | HASH | 战斗状态: status, turn, participants_json | - (战斗结束删除) |
| `wx:battle:turn:timer:{battle_id}` | STRING | 回合计时器标志 | 45s |
| `wx:team:{team_id}` | HASH | 队伍信息: leader_id, members_json | - |
| `wx:team:member:{char_id}` | STRING | 角色所在队伍ID | - |
| `wx:chat:channel:{channel_id}` | LIST | 频道聊天历史(最近100条) | - |
| `wx:chat:world:cd:{char_id}` | STRING | 世界频道发言冷却 | 30s |
| `wx:guild:online:{guild_id}` | SET | 帮派在线成员集合 | - |
| `wx:lock:{lock_key}` | STRING | 分布式锁 | 10s(自动释放) |
| `wx:ratelimit:{char_id}:{action}` | STRING | 操作限流计数器 | 1min/1h等 |
| `wx:quest:daily:{char_id}:{date}` | HASH | 日常任务次数统计: shimen_count, zhuagui_count等 | 48h |
| `wx:buff:{char_id}:{buff_id}` | STRING | BUFF剩余时间 | 按buff时长 |
| `wx:encounter:cd:{char_id}` | STRING | 遇敌冷却，防止连续遇敌 | 3s |
| `wx:move:cd:{char_id}` | STRING | 移动冷却，防瞬移 | 1s |
| `wx:nonce:{nonce}` | STRING | 请求防重放nonce | 5min |
| `wx:jwt:blacklist:{jti}` | STRING | JWT黑名单 | 到token过期 |
| `wx:ban:char:{char_id}` | HASH | 角色封禁信息: ban_type, reason, until | 封禁时长 |
| `wx:ban:user:{user_id}` | HASH | 账号封禁信息 | 封禁时长 |
| `wx:ratelimit:ip:{ip}:{minute}` | STRING | IP限流计数器 | 2min |
| `wx:anticheat:reaction:{char_id}` | LIST | 战斗反应时间记录(最近20次) | 24h |
| `wx:anticheat:move_path:{char_id}` | LIST | 最近移动路径点(用于异常检测) | 10min |
| `wx:lock:bag:{char_id}` | STRING | 背包操作分布式锁 | 10s |
| `wx:lock:trade:{trade_id}` | STRING | 交易操作锁 | 30s |
| `wx:captcha:char:{char_id}` | STRING | 需要验证码标志 | 30min |

---

## 5. API接口设计

### 5.1 REST API 统一规范

**基础路径**: `/api/v1`

**请求头**:
```
Authorization: Bearer {jwt_token}
Content-Type: application/json
```

**统一响应格式**:
```json
{
  "code": 0,           // 0成功，非0错误码
  "message": "success",// 消息
  "data": { ... }      // 数据
}
```

**分页响应格式**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}
```

### 5.2 核心API列表

#### 认证模块 `/api/v1/auth`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/register` | 用户注册 |
| POST | `/login` | 用户登录，返回JWT |
| POST | `/refresh` | 刷新Token |
| POST | `/logout` | 登出(Token黑名单) |
| GET | `/me` | 获取当前用户信息 |

#### 角色模块 `/api/v1/character`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list` | 获取当前账号下角色列表 |
| POST | `/create` | 创建新角色 |
| POST | `/select/{char_id}` | 选择角色进入游戏 |
| GET | `/info` | 获取当前角色详细信息(含属性) |
| POST | `/pot/add` | 分配潜力点 |
| GET | `/skills` | 获取门派技能列表 |
| POST | `/skills/{skill_id}/learn` | 学习技能 |
| GET | `/practice` | 获取修炼等级 |
| POST | `/practice/{type}/upgrade` | 点修炼 |

#### 地图与移动 `/api/v1/map`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/current` | 获取当前地图信息 |
| GET | `/list` | 获取所有地图列表 |
| GET | `/{map_id}` | 获取地图详情 |
| POST | `/move` | 移动到相邻地图 {target_map_id} |
| POST | `/goto` | 坐标移动 {x, y} |
| GET | `/npcs` | 获取当前场景NPC列表 |
| POST | `/npc/talk` | 与NPC对话 {npc_id} |
| POST | `/npc/teleport` | 使用NPC传送 {npc_id} |

#### 战斗模块 `/api/v1/battle`
| 方法 | 路径 | 说明 |
|------|------|------|
| WS | `/ws/battle/{battle_id}` | 战斗WebSocket连接 |
| POST | `/command` | 提交战斗指令(通过WS发送) |
| GET | `/history/{battle_id}` | 获取战斗记录 |

*注: 战斗实时操作全部通过WebSocket进行*

#### 物品装备 `/api/v1/item`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/bag` | 获取背包物品列表 |
| GET | `/equipped` | 获取已装备物品 |
| POST | `/equip` | 装备物品 {char_item_id} |
| POST | `/unequip` | 卸下装备 {slot} |
| POST | `/use` | 使用物品 {char_item_id, target_id?} |
| POST | `/discard` | 丢弃物品 {char_item_id, count} |

#### 宠物模块 `/api/v1/pet`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/list` | 获取我的宠物列表 |
| GET | `/{pet_id}` | 获取宠物详情 |
| POST | `/set-battle` | 设置出战宠物 {pet_id} |
| POST | `/feed` | 喂宠物(恢复忠诚/寿命) |
| POST | `/release` | 放生宠物 {pet_id} |
| POST | `/learn-skill` | 宠物打书 {pet_id, item_id(魔兽要诀)} |

#### 任务模块 `/api/v1/quest`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/current` | 获取当前进行中的任务 |
| GET | `/available` | 获取可接取任务列表 |
| POST | `/accept/{quest_id}` | 接取任务 |
| POST | `/submit/{quest_id}` | 提交任务 |
| POST | `/abandon/{quest_id}` | 放弃任务 |
| GET | `/shimen/status` | 获取今日师门任务状态 |
| POST | `/shimen/start` | 开始今日师门 |
| GET | `/zhuagui/status` | 获取本周/今日抓鬼状态 |
| POST | `/zhuagui/start` | 领抓鬼任务 |
| GET | `/hubiao/status` | 获取护镖状态 |
| POST | `/hubiao/start` | 领取镖银 |
| GET | `/dungeon/list` | 获取可进入副本 |
| POST | `/dungeon/enter/{dungeon_id}` | 进入副本 |

#### 社交模块 `/api/v1/social`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/chat/send` | 发送聊天消息 {channel, content, target_id?} |
| GET | `/chat/history/{channel}` | 获取频道历史 |
| GET | `/friends` | 获取好友列表 |
| POST | `/friends/add` | 添加好友 {char_name} |
| POST | `/friends/remove` | 删除好友 {friend_id} |
| GET | `/team/info` | 获取当前队伍信息 |
| POST | `/team/create` | 创建队伍 |
| POST | `/team/invite` | 邀请入队 {char_id} |
| POST | `/team/accept` | 接受入队邀请 |
| POST | `/team/kick` | 踢人 {char_id} |
| POST | `/team/leave` | 离队 |
| POST | `/team/transfer` | 转让队长 {char_id} |

#### 帮派模块 `/api/v1/guild`
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/info` | 获取当前帮派信息 |
| GET | `/list` | 获取帮派列表 |
| POST | `/create` | 创建帮派 {name, announcement} |
| POST | `/apply/{guild_id}` | 申请加入 |
| POST | `/approve` | 审批申请 {char_id, approve:bool} |
| POST | `/leave` | 离开帮派 |
| GET | `/members` | 获取帮派成员列表 |
| POST | `/member/promote` | 成员职位调整 {char_id, position} |
| POST | `/member/kick` | 踢出成员 {char_id} |
| GET | `/skills` | 获取帮派技能列表 |
| POST | `/skills/learn` | 学习帮派技能 {skill_id} |
| GET | `/tasks` | 获取帮派任务列表 |
| POST | `/tasks/start/{task_type}` | 领取帮派任务 |

#### 经济模块 `/api/v1/economy`
| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/shop/buy` | 从NPC商店购买 {npc_id, item_config_id, count} |
| POST | `/shop/sell` | 卖给NPC {char_item_id, count} |
| POST | `/trade/request` | 请求交易 {target_id} |
| POST | `/trade/accept` | 接受交易请求 {trade_id} |
| POST | `/trade/add-item` | 交易添加物品 {trade_id, char_item_id} |
| POST | `/trade/add-cash` | 交易添加现金 {trade_id, amount} |
| POST | `/trade/confirm` | 确认交易 |
| POST | `/trade/cancel` | 取消交易 |
| POST | `/stall/open` | 摆摊 {title} |
| POST | `/stall/add-item` | 上架物品 {char_item_id, price} |
| POST | `/stall/buy` | 买摊位物品 {stall_item_id} |
| POST | `/stall/close` | 收摊 |
| GET | `/recharge/orders` | 获取充值订单 |
| POST | `/recharge/create` | 创建充值订单 {amount, channel} |
| GET | `/shop/mall/list` | 获取商城物品列表 |
| POST | `/shop/mall/buy` | 购买商城物品 {mall_item_id} |

#### 全局游戏WebSocket `/ws/game`
游戏主连接，建立后接收所有游戏推送、聊天消息、状态更新等。

---

## 6. WebSocket消息协议设计

### 6.1 连接
- 游戏主WS: `ws://{host}/ws/game?token={jwt}`
- 战斗WS: `ws://{host}/ws/battle/{battle_id}?token={jwt}`

### 6.2 消息通用格式
客户端→服务端:
```json
{
  "type": "cmd_type",
  "data": { ... },
  "msg_id": "uuid-xxx",  
  "timestamp": 1234567890
}
```

服务端→客户端:
```json
{
  "type": "event_type",
  "data": { ... },
  "msg_id": "uuid-xxx",
  "code": 0,
  "message": "success",
  "timestamp": 1234567890
}
```

### 6.3 客户端消息类型 (C2S)

| type | 说明 | data |
|------|------|------|
| `heartbeat` | 心跳 | - |
| `chat` | 发送聊天 | {channel, content, target_id?} |
| `battle_cmd` | 战斗指令 | {battle_id, action_type, target_id?, skill_id?, item_id?} |
| `team_operation` | 队伍操作 | {op: invite/kick/accept/leave/transfer, char_id?} |
| `trade_operation` | 交易操作 | {op: accept/add_item/add_cash/confirm/cancel, ...} |

### 6.4 服务端推送消息类型 (S2C)

| type | 说明 | data |
|------|------|------|
| `connected` | 连接成功 | {char_id, char_name, server_time} |
| `heartbeat_ack` | 心跳响应 | {server_time} |
| `error` | 错误 | {code, message} |
| `system_notice` | 系统公告 | {content, level} |
| `world_enter` | 进入场景 | {map_id, map_name, npcs, players} |
| `world_players_update` | 场景玩家变化 | {entered: [], left: []} |
| `player_move` | 玩家移动 | {char_id, name, from_x, from_y, to_x, to_y} |
| `chat_message` | 聊天消息 | {channel, speaker_id, speaker_name, content, send_time} |
| `battle_invite` | 战斗邀请(组队遇敌/被PK) | {battle_id, reason, inviter_id?} |
| `battle_start` | 战斗开始 | {battle_id, participants: [], turn: 1} |
| `battle_turn_start` | 回合开始 | {turn, time_left} |
| `battle_action` | 战斗行动播报 | {actor_id, action_type, targets: [{target_id, damage, is_crit, is_dead}], effect_text} |
| `battle_turn_end` | 回合结束 | {participants_state: []} |
| `battle_end` | 战斗结束 | {result: win/lose/escape, rewards: {exp, cash, items: []}} |
| `battle_your_turn` | 轮到你行动 | {time_left} |
| `quest_progress` | 任务进度更新 | {quest_id, quest_name, step, progress_text} |
| `quest_complete` | 任务可完成 | {quest_id, quest_name, npc_id} |
| `level_up` | 升级 | {old_level, new_level, new_pot_points} |
| `item_gain` | 获得物品 | {item_id, item_name, count} |
| `item_lose` | 失去物品 | {item_id, item_name, count} |
| `cash_change` | 金钱变化 | {cash_delta, reserve_delta, reason} |
| `jade_change` | 仙玉变化 | {jade_delta, reason} |
| `hp_change` | 气血变化 | {hp, hp_max, mp, mp_max} |
| `buff_gain` | 获得BUFF | {buff_id, buff_name, duration} |
| `buff_lose` | 失去BUFF | {buff_id, buff_name} |
| `team_update` | 队伍变化 | {leader_id, members: []} |
| `trade_request` | 收到交易请求 | {trade_id, initiator_name} |
| `trade_update` | 交易状态变化 | {trade_id, our_items, their_items, our_cash, their_cash} |
| `friend_request` | 好友申请 | {from_id, from_name} |
| `guild_invite` | 帮派邀请 | {guild_id, guild_name, inviter_name} |
| `guild_chat` | 帮派聊天 | (同chat_message) |
| `shimen_task_update` | 师门任务更新 | {round, task_desc, target_npc, target_map} |
| `zhuagui_task_update` | 抓鬼任务更新 | {round, ghost_type, map_name, coord} |
| `hubiao_status` | 护镖状态 | {status, current_map, target_map, target_npc, danger_level} |
| `dungeon_progress` | 副本进度 | {dungeon_id, dungeon_name, current_fight, total_fights} |

*预留UI字段: 所有涉及实体的消息(玩家/怪物/NPC/物品/技能)都携带 `resource_id` 和 `sprite_data` (可选)，二期UI客户端可直接用于渲染。*

---

## 7. 核心模块详细设计

### 7.1 战斗引擎设计 (核心)

战斗系统是游戏最核心的模块，采用**回合制状态机**设计。

#### 7.1.1 战斗流程
```
创建战斗(分配battle_id, 初始化参战者)
    ↓
[回合N开始]
    ↓
按速度排序所有参战者 → 发送battle_turn_start
    ↓
等待玩家提交指令 (有45秒超时，超时默认防御)
    ↓
按顺序执行每个参战者的行动:
    - 计算命中/闪避/暴击/保护
    - 计算伤害/治疗/封印/增益/减益
    - 发送battle_action播报
    - 检查一方全灭 → 若全灭则战斗结束
    ↓
回合结束处理:
    - 结算BUFF/DEBUFF持续时间
    - 执行DOT/HOT伤害/治疗
    - MP/愤怒自然恢复
    - 发送battle_turn_end
    ↓
检查战斗是否结束 → 未结束则进入下一回合
    ↓
战斗结束 → 结算奖励(经验/金钱/掉落) → 保存战斗日志 → 发送battle_end
```

#### 7.1.2 伤害计算公式
```
物理伤害结果 = (己方伤害 - 敌方防御) * 修炼差系数 * 阵型系数 * 修炼差 * 随机浮动(0.9~1.1)
法术伤害结果 = (己方法伤 - 敌方法防) * 技能系数 * 修炼差系数 * 阵型系数 * 随机浮动(0.9~1.1)
修炼差系数 = 1 + (己方攻法修炼 - 对方法防修炼)*0.02 + (对方法防修炼-己方攻法修炼)*0.02(最小0.2)
暴击判定: 必杀技能/暴击Buff → 伤害*1.5~2倍
命中判定: 己方命中 vs 敌方闪避 (速度影响)，初始命中率85%
```

#### 7.1.3 战斗指令处理类结构
```python
class BattleEngine:
    """战斗引擎，无状态纯逻辑，便于单元测试"""
    
    def init_battle(self, config: BattleConfig) -> BattleState:
        """初始化战斗状态"""
        
    def submit_command(self, state: BattleState, char_id: int, cmd: BattleCommand) -> None:
        """提交战斗指令"""
        
    def resolve_turn(self, state: BattleState) -> List[BattleAction]:
        """结算当前回合，返回所有行动日志"""
        # 1. 检查所有玩家指令是否就绪/超时
        # 2. 按速度排序
        # 3. 依次执行每个单位的行动
        # 4. 检查战斗结束
        # 5. BUFF结算
        
    def calculate_damage(self, attacker: BattleUnit, target: BattleUnit, skill: SkillConfig) -> DamageResult:
        """计算伤害"""
        
    def check_battle_end(self, state: BattleState) -> Optional[BattleResult]:
        """检查战斗是否结束"""
        
    def settle_rewards(self, state: BattleState, result: BattleResult) -> BattleRewards:
        """结算奖励"""
```

### 7.2 任务系统设计

任务采用**配置驱动+步骤状态机**设计，所有任务类型统一接口。

```python
class QuestHandler(ABC):
    """任务处理器基类"""
    
    quest_type: QuestType  # 任务类型
    
    @abstractmethod
    def can_accept(self, char: Character, quest_config: QuestConfig) -> Tuple[bool, str]:
        """检查是否可接取"""
        
    @abstractmethod
    def on_accept(self, char: Character, quest_state: CharacterQuest) -> None:
        """接取时初始化步骤"""
        
    @abstractmethod
    def get_progress_text(self, quest_state: CharacterQuest) -> str:
        """获取当前进度描述"""
        
    @abstractmethod
    def check_complete(self, char: Character, quest_state: CharacterQuest) -> bool:
        """检查是否完成"""
        
    @abstractmethod
    def on_complete(self, char: Character, quest_state: CharacterQuest) -> QuestRewards:
        """完成时结算奖励"""
        
    def on_event(self, char: Character, quest_state: CharacterQuest, event: GameEvent) -> None:
        """游戏事件触发(战斗胜利/NPC对话/获得物品等)，用于更新进度"""


class ShimenQuest(QuestHandler):
    """师门任务处理器
    每日20轮，每轮从任务池中随机:
    - 送信: 找某个NPC对话
    - 巡逻: 在门派地图战斗3场
    - 采购: 索要某个物品
    - 示威: 去某个地图教训NPC(战斗)
    奖励按轮次递增，第10轮/第20轮额外奖励
    """

class ZhuaguiQuest(QuestHandler):
    """抓鬼任务处理器
    组队找钟馗领取，按等级生成鬼怪坐标
    鬼怪类型: 血鬼(高HP)、僵尸(高血高攻)、牛头(高抗物理)、马面(高抗法)、骷髅(高闪避)、野鬼(低血低灵)
    每轮完成经验递增，第10轮队长必得物品奖励
    """

class HubiaoQuest(QuestHandler):
    """护镖任务处理器
    交押金，领取镖银，押送路线是从长安到指定门派/场景
    途中会有劫镖怪物出现，战斗胜利继续，失败损失押金
    每人每天可押50次，等级越高押金越高奖励越好
    """

class DungeonQuest(QuestHandler):
    """副本任务处理器
    建邺城除妖(一期副本):
    - 组队5人进入副本场景
    - 依次进行4场小怪战斗
    - 最后BOSS战: 妖风(主怪) + 4个小怪
    - BOSS有技能: 群攻、召唤小怪
    - 胜利后每人掷骰子，按点数分配掉落物品
    """
```

### 7.3 命令解析系统设计

文字版核心交互是命令解析，采用**命令模式+前缀匹配**。

```python
class CommandParser:
    """命令解析器"""
    
    _commands: Dict[str, CommandHandler]
    
    def register(self, handler: CommandHandler):
        """注册命令处理器"""
        
    async def parse_and_execute(self, char_id: int, text: str) -> CommandResult:
        """解析并执行命令"""
        # 1. 按空格分词
        # 2. 第一个词为命令名，支持缩写匹配(/go, /zou)
        # 3. 后续为参数
        # 4. 参数自动类型转换与校验
        # 5. 执行对应handler
        # 6. 返回执行结果(文字消息或跳转)

# 常用命令:
# /go [地图名]        - 去地图，如 /go 长安
# /move [方向]        - 上下左右移动，如 /move 东
# /look               - 查看当前场景
# /talk [NPC名]       - 与NPC对话
# /fight              - 开始切磋/强行攻击(PK需开关)
# /skill              - 查看技能
# /use [物品名]       - 使用物品
# /equip [物品名]     - 装备
# /bag                - 查看背包
# /pet                - 查看宠物
# /quest              - 查看任务
# /team               - 查看队伍
# /team invite [人名] - 组队邀请
# /friend add [人名]  - 加好友
# /chat [频道] [内容] - 聊天，如 /chat 世界 大家好
# /who                - 查看当前场景玩家
# /join [队伍]        - 申请入队
# /leave              - 离队
# /shimen             - 领取师门任务
# /zhuagui            - 领抓鬼任务
# /hubiao             - 领镖
# /shop               - 打开商店(在商店NPC旁)
# /trade [人名]       - 交易
# /stall open         - 摆摊
# /help [命令]        - 帮助
```

---

## 8. 安全与防作弊设计

### 8.1 核心原则：前端数据完全不可信
**所有客户端上报的数据都必须经过服务端校验，前端仅作为输入/展示终端。**

```
前端 → 提交操作 → 服务端校验(位置/状态/权限/冷却/资源) → 执行操作 → 推送最新状态 → 前端渲染
```

### 8.2 防接口刷资源
1. **请求签名与防重放**
   - REST API和WebSocket消息都携带 `nonce`(随机字符串) + `timestamp` + `signature`
   - signature = HMAC-SHA256(secret, body + timestamp + nonce)
   - 服务端校验timestamp与服务器时间差不超过5分钟
   - nonce存入Redis，5分钟内重复nonce视为重放攻击，拒绝并记录
   - 一期简化版: 仅依赖HTTPS + JWT + 请求频率限制，签名在二期UI客户端启用

2. **多层频率限制(Redis滑动窗口)**
   ```
   全局: 单IP每分钟最多200次请求
   用户: 单用户每分钟最多100次请求
   移动: 1秒CD，相邻两次移动距离不能超过单步上限
   战斗指令: 单场战斗每回合最多提交1次指令，3秒内重复提交直接丢弃
   世界聊天: 30秒CD，1分钟最多3条，1小时最多30条
   私聊: 1秒CD，1分钟最多20条，防止骚扰
   交易/摆摊: 10秒CD，防止刷交易
   接取/提交任务: 3秒CD
   购买物品: 2秒CD，单次购买数量不超过上限
   NPC对话: 500msCD
   ```
   - 触发限流返回明确错误码，首次警告，连续触发临时封禁1-24小时

3. **资源操作原子性校验**
   - **背包操作分布式锁**: `wx:lock:bag:{char_id}`，物品增减/装备/交易/丢弃必须持有锁
   - **金钱/仙玉操作**: 所有货币变动使用数据库行锁 + 乐观锁(version字段)，变动前后校验余额≥0
   - **物品唯一ID校验**: 每个物品实例有唯一ID，操作时校验`owner_id`确实是当前角色
   - **购买校验**: 买东西时校验：NPC是否在当前场景、商店是否售卖该物品、价格是否匹配、金钱是否足够
   - **任务奖励防重复领取**: 任务状态+数据库唯一约束，提交任务时使用事务保证奖励只发一次

4. **关键操作日志审计**
   - 所有涉及资源变动的操作(物品获得/失去、金钱变动、仙玉变动、交易、充值、商城购买、GM操作)都记录 `operation_logs` 表
   - 日志字段: char_id, action, detail_json, ip, user_agent, timestamp
   - 异常流水检测: 短时间内获得大量物品/金钱、与低等级角色交易大量资产、连续向同一账号角色转移资源自动标记

### 8.3 防篡改网页数据
1. **前端不存储关键状态**
   - 气血/魔法/金钱/经验/背包物品/任务进度等所有状态以服务端数据为准
   - 前端只展示服务端推送的状态，前端本地状态不可信，不做逻辑判断
   - 禁止前端直接写localStorage/sessionStorage关键数据，只缓存非敏感UI状态
   - 每次操作后服务端推送最新状态快照，前端全量覆盖本地状态

2. **状态校验点**
   - **移动校验**: 传入目标坐标时，服务端校验：
     * 角色当前map_id是否正确
     * from坐标是否与服务端记录一致(防止瞬移)
     * 目标坐标是否在地图合法范围内
     * 目标地图是否相邻(跨地图移动)
     * 移动CD是否满足
   - **战斗指令校验**:
     * 角色是否在战斗中(battle_id匹配)
     * 当前回合是否已经提交过指令
     * 使用的技能是否已学习、MP是否足够
     * 使用的物品是否在背包中、是否在战斗中可用
     * 攻击目标是否合法(敌方/已方/存活)
   - **使用物品校验**:
     * 物品是否属于自己
     * 物品CD是否满足
     * 药品使用目标是否在场/存活
   - **交易校验**:
     * 双方是否在同一地图、距离是否足够近(5格内)
     * 交易双方都不能在战斗中/摆摊中/其他交易中
     * 锁定后不能再修改物品/金钱
     * 确认时二次校验双方物品/金钱是否仍存在(防止中途转移)

3. **WebSocket连接安全**
   - 连接建立时一次性校验JWT，校验通过后绑定char_id与conn_id
   - 一个角色同时只能有一个WS连接，新连接建立自动踢掉旧连接(防止多开)
   - 所有WS消息必须来自对应char_id的连接，禁止伪造他人消息
   - 心跳机制: 每30秒发心跳，90秒无心跳服务器主动断开
   - 消息长度限制: 单条消息不超过4KB，防止恶意大包
   - 连接建立后服务端立即推送一次角色全量状态，前端用此状态初始化

4. **禁止直接暴露内部ID**
   - 对外暴露的角色ID/物品ID使用加密ID(如hashid)，不直接使用数据库自增ID/雪花ID
   - 防止玩家遍历ID猜测其他用户信息
   - 管理后台可通过原始ID查询，但客户端API只接受加密ID

### 8.4 防外挂/自动化检测
1. **行为模式分析**
   - **操作时间分布异常**: 人类操作间隔有自然波动(100ms-几秒随机)，外挂操作间隔恒定(<10ms方差)标记可疑
   - **移动路径异常**: 不走常规路径、穿墙、斜向走连续长距离、到点精准无误差
   - **战斗反应异常**: 回合开始后<200ms就提交指令，且连续多回合如此，标记为脚本
   - **在线时长异常**: 24小时连续在线且无自然休息间隔
   - **刷怪效率异常**: 单位时间内遇敌/战斗次数远超人力极限(带练/脚本)

2. **验证码机制**
   - 可疑用户触发图形验证码/行为验证码，验证通过才能继续操作
   - 验证码连续3次错误，强制下线15分钟
   - 新注册账号前10次关键操作(第一次交易、第一次摆摊、第一次高价值物品丢弃)需要验证码

3. **内存/数据篡改防护(二期UI端)**
   - 一期文字Web端依赖浏览器环境，重点在服务端校验
   - 二期Unity/Cocos客户端：
     * 关键内存数据做校验和，异常时强制断线
     * 客户端与服务端定期状态校验(位置/HP/物品数)，不一致踢下线
     * 检测常见调试器/修改器并上报

### 8.5 经济系统防护
1. **产出与消耗监控**
   - 每日统计全服金钱/物品/经验产出量与消耗量，偏离正常值±30%告警
   - 每个玩法的产出效率设置上限，超过上限触发衰减机制(如师门超过20轮收益减半)
   - 高价值物品(装备/宠物/兽决)获得/交易/销毁全链路留痕，每一件都可追溯来源

2. **交易限制**
   - 新号(等级<30)不能交易、不能摆摊，只能与NPC交互
   - 低等级角色携带金钱上限随等级提升，超出部分下线后转为储备金
   - 交易物品价格异常(低于市场价30%或高于市场价300%)标记可疑，高价值物品交易冻结24小时
   - 仙玉/商城道具绑定(装备后绑定/拾取绑定)，防止刷商城倒卖

3. **漏洞应急机制**
   - 发现刷资源漏洞时，可通过管理后台一键：
     * 回滚指定时间段内指定玩家的物品/金钱变动
     * 临时关闭相关玩法入口
     * 封禁可疑账号
     * 全服公告说明

### 8.6 基础安全措施
- 密码使用bcrypt加密(cost=12)，慢哈希防彩虹表，不存储明文密码
- JWT使用HS256强随机密钥(≥64字节)，access_token 1小时过期，refresh_token 7天过期
- Token黑名单机制(Redis存储已注销/刷新的token到过期)
- WebSocket连接建立验证Token后绑定char_id，后续消息不重复校验Token但校验连接归属
- 敏感词过滤DFA算法，聊天/昵称/帮派名/摊位名实时过滤，违规词替换为***，多次违规禁言
- 管理后台：
  * 独立域名/端口
  * IP白名单(只允许办公网IP访问)
  * 二次验证码(Google Authenticator)
  * 管理员权限分级，操作留痕，不可删除日志
- SQL注入防护: SQLAlchemy ORM参数化查询，禁止拼接SQL
- XSS防护: 前端React默认转义，服务端响应头设置X-XSS-Protection
- CSRF防护: SameSite Cookie + JWT Authorization头
- HTTPS全站加密，WAF防护常见攻击
- 充值接口：
  * 订单号全局唯一
  * 支付回调验签
  * 幂等处理，重复回调不重复发货
  * 订单金额与仙玉数量后端校验，不采信前端传值

### 8.7 数据库安全
- 应用使用最小权限数据库账号(只有CRUD，无DROP/ALTER权限)
- 数据库端口不对外暴露，只允许应用服务器内网访问
- 定期自动备份(每日全量+实时WAL归档)，备份异地存储
- 管理操作(修改物品/发放仙玉)必须双人复核，操作日志永久保存


---

## 9. 测试策略

### 9.1 测试分层
```
E2E测试(10%) ← 主流程跑通，少量覆盖
    ↑
集成测试(30%) ← API/WebSocket接口测试，数据库+Redis真实环境
    ↑
单元测试(60%) ← 核心逻辑100%覆盖，Mock外部依赖
```

### 9.2 单元测试重点
1. **战斗引擎** (100%覆盖)
   - 伤害计算各种情况(0防御、修炼差、暴击、保护)
   - 技能效果(群攻、治疗、封印、复活)
   - 宠物指令、道具使用
   - 特殊战斗(抓鬼不同鬼、副本BOSS技能)
   - 组队战斗、宠物自动AI
   - 战斗超时、断线重连处理

2. **任务逻辑**
   - 师门任务各类型完成条件
   - 抓鬼轮次与奖励
   - 护镖劫镖战斗
   - 副本流程与掉落分配

3. **计算公式**
   - 升级经验计算
   - 属性点换算成战斗属性
   - 修炼加成
   - 掉落概率与随机分布

4. **物品背包**
   - 堆叠逻辑
   - 装备切换
   - 物品使用冷却
   - 背包满时处理

### 9.3 集成测试
- 使用测试数据库(PostgreSQL TestContainers或独立test库)
- 使用测试Redis(db=15)
- FastAPI TestClient模拟API请求
- 测试注册→创建角色→进入游戏→移动→遇敌→战斗→完成任务→获得物品→升级完整链路
- WebSocket测试: 连接→收发消息→战斗指令→断线重连

### 9.4 测试技术栈
- 后端: pytest + pytest-asyncio + httpx + pytest-redis + factory-boy(测试数据工厂)
- 前端: Jest + React Testing Library + MSW(Mock Service Worker)
- E2E: pytest + requests + websockets客户端(后端驱动) 或 Playwright(前端)

### 9.5 测试命令
```bash
# 后端测试
cd backend
pytest tests/ -v --cov=app --cov-report=term-missing

# 前端测试
cd frontend
npm test -- --coverage
```

---

## 10. 部署架构

### 10.1 Docker Compose 部署(一期单机)
```yaml
services:
  postgres:
    image: postgres:15-alpine
    volumes:
      - pg_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: wenxi
      POSTGRES_USER: wenxi
      POSTGRES_PASSWORD: xxx
  
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
  
  backend:
    build: ./backend
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql+asyncpg://...
      - REDIS_URL=redis://redis:6379/0
    ports:
      - "8000:8000"
  
  frontend:
    build: ./frontend
    ports:
      - "3000:80"
  
  admin:
    build: ./admin
    ports:
      - "3001:80"
  
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
    depends_on:
      - backend
      - frontend
      - admin

volumes:
  pg_data:
  redis_data:
```

### 10.2 环境配置
- `.env` 文件管理环境变量
- dev/staging/prod三套环境配置隔离
- 生产环境密钥通过环境变量注入，不硬编码

---

## 11. 二期扩展预留点

1. **分服/跨服**: 数据库设计预留server_id字段，Redis按server分库
2. **图形客户端**: 所有实体有resource_id，战斗消息包含完整快照
3. **更多门派/宠物/技能**: 配置表驱动，只需在管理后台添加配置即可
4. **帮战/PVP活动**: 战斗引擎已支持多对多，增加匹配和地图逻辑即可
5. **家园/生活技能**: 使用quest/guild类似的扩展机制，不改动核心
6. **移动端**: API层无状态，直接复用接口
