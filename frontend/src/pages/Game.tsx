import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Tabs, Input, Button, List, Tag, Space, message, Modal, Form, Progress, Card, Statistic } from 'antd'
import {
  UserOutlined, EnvironmentOutlined, ShoppingOutlined, SnippetsOutlined,
  TeamOutlined, SendOutlined, LogoutOutlined, ThunderboltOutlined,
  MedicineBoxOutlined, ArrowUpOutlined, ArrowDownOutlined, ArrowLeftOutlined, ArrowRightOutlined
} from '@ant-design/icons'
import api from '../api/client'
import { useGameStore } from '../store/game'

export default function Game() {
  const nav = useNavigate()
  const { char, messages, inBattle, setChar, addMessage, setBattle, logout } = useGameStore()
  const [mapInfo, setMapInfo] = useState<any>(null)
  const [bag, setBag] = useState<any[]>([])
  const [quests, setQuests] = useState<any[]>([])
  const [chatInput, setChatInput] = useState('')
  const [cmdInput, setCmdInput] = useState('')
  const outputRef = useRef<HTMLDivElement>(null)
  const [ws, setWs] = useState<WebSocket | null>(null)

  const loadChar = async () => {
    try {
      const { data } = await api.get('/character/info')
      setChar(data)
      addMessage('system', `欢迎回来，${data.name}！你当前在 Lv.${data.level}`)
    } catch (e: any) {
      if (e.response?.status === 401) nav('/login')
    }
  }

  const loadMap = async () => {
    try {
      const { data } = await api.get('/map/current')
      setMapInfo(data)
    } catch (e) {
      // ignore
    }
  }

  const loadBag = async () => {
    try {
      const { data } = await api.get('/item/bag')
      setBag(data)
    } catch (e) {}
  }

  const loadQuests = async () => {
    try {
      const { data } = await api.get('/quest/current')
      setQuests(data)
    } catch (e) {}
  }

  useEffect(() => {
    loadChar()
    loadMap()
    loadBag()
    loadQuests()
    const token = localStorage.getItem('access_token')
    const charId = localStorage.getItem('char_id')
    if (token && charId) {
      const proto = location.protocol === 'https:' ? 'wss' : 'ws'
      const socket = new WebSocket(`${proto}://${location.host}/ws?token=${token}&char_id=${charId}`)
      socket.onopen = () => {
        addMessage('system', '实时连接已建立')
      }
      socket.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data)
          if (msg.type === 'connected') {
            addMessage('system', `已连接为 ${msg.name}`)
          } else if (msg.type === 'chat') {
            addMessage('chat', `[${msg.data.channel}] ${msg.data.speaker_name}: ${msg.data.content}`)
          } else if (msg.type === 'battle') {
            addMessage('combat', `战斗: ${JSON.stringify(msg.data)}`)
          } else if (msg.type === 'battle_resolved') {
            addMessage('combat', `回合结果: ${JSON.stringify(msg.data)}`)
            loadChar()
          } else if (msg.type === 'error') {
            message.error(msg.msg)
          }
        } catch (e) {}
      }
      socket.onclose = () => {
        addMessage('system', '连接已断开，正在重连...')
      }
      setWs(socket)
      return () => socket.close()
    }
  }, [])

  useEffect(() => {
    if (outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight
    }
  }, [messages])

  const doMove = async (dir: string) => {
    try {
      const { data } = await api.post('/map/move/coord', { direction: dir })
      await loadMap()
      await loadChar()
      if (data.encounter) {
        addMessage('combat', '⚠️ 遇到了怪物！')
        await startBattle()
      }
    } catch (e: any) {
      message.error(e.response?.data?.msg || '移动失败')
    }
  }

  const startBattle = async () => {
    try {
      const { data } = await api.post('/battle/start/random')
      if (data.battle_id) {
        setBattle(true, data)
        addMessage('combat', `战斗开始！遭遇敌人！`)
      }
    } catch (e: any) {
      addMessage('system', '这里没有敌人')
    }
  }

  const battleAttack = async () => {
    try {
      const { data: state } = await api.get('/battle/state')
      if (state.in_battle) {
        const enemy = state.enemy_units.find((u: any) => u.is_alive)
        await api.post('/battle/command', { action_type: 'attack', target_unit_id: enemy?.unit_id })
        const { data } = await api.post('/battle/resolve', {})
        addMessage('combat', data.log || '攻击！')
        if (data.ended) {
          setBattle(false)
          addMessage('reward', `战斗胜利！获得经验${data.exp_gained || 0}，金币${data.cash_gained || 0}`)
          await loadChar()
          await loadBag()
        }
      }
    } catch (e: any) {
      message.error(e.response?.data?.msg || '战斗指令失败')
    }
  }

  const battleEscape = async () => {
    try {
      await api.post('/battle/command', { action_type: 'escape' })
      const { data } = await api.post('/battle/resolve', {})
      addMessage('combat', data.fled ? '逃跑成功！' : '逃跑失败！')
      if (data.ended || data.fled) {
        setBattle(false)
        await loadChar()
      }
    } catch (e: any) {
      message.error(e.response?.data?.msg || '逃跑失败')
    }
  }

  const sendChat = () => {
    if (!chatInput.trim()) return
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'chat', channel: 'world', content: chatInput }))
    }
    setChatInput('')
  }

  const doHeal = async () => {
    try {
      await api.post('/character/heal')
      addMessage('reward', '治疗完成！')
      loadChar()
    } catch (e: any) {
      message.error(e.response?.data?.msg || '治疗失败')
    }
  }

  const useItem = async (item: any) => {
    try {
      await api.post('/item/use', { char_item_id: item.instance_id })
      addMessage('reward', `使用了${item.name}`)
      loadChar()
      loadBag()
    } catch (e: any) {
      message.error(e.response?.data?.msg || '使用失败')
    }
  }

  const doLogout = () => {
    if (ws) ws.close()
    logout()
    nav('/login')
  }

  const hpPct = char ? Math.round((char.hp / char.hp_max) * 100) : 0
  const mpPct = char ? Math.round((char.mp / char.mp_max) * 100) : 0
  const expPct = char && char.next_exp ? Math.round((char.exp / char.next_exp) * 100) : 0

  return (
    <div className="game-container">
      <div className="status-bar">
        <Space>
          <UserOutlined />
          <span>{char?.name}</span>
          <Tag color="gold">Lv.{char?.level}</Tag>
          <span>HP</span>
          <div className="hp-bar"><div style={{ width: `${hpPct}%` }} /></div>
          <span style={{ fontSize: 12 }}>{char?.hp}/{char?.hp_max}</span>
          <span>MP</span>
          <div className="hp-bar mp-bar"><div style={{ width: `${mpPct}%` }} /></div>
          <span style={{ fontSize: 12 }}>{char?.mp}/{char?.mp_max}</span>
        </Space>
        <Space>
          <Tag color="yellow">💰 {char?.cash?.toLocaleString()}</Tag>
          <EnvironmentOutlined /> {mapInfo?.name} ({char?.pos_x},{char?.pos_y})
          <Button size="small" danger icon={<LogoutOutlined />} onClick={doLogout}>退出</Button>
        </Space>
      </div>

      <div className="game-main">
        <div className="panel scene-panel">
          <div className="scene-output" ref={outputRef}>
            {messages.map((m, i) => (
              <div key={i} className={m.type}>[{new Date(m.time).toLocaleTimeString()}] {m.text}</div>
            ))}
          </div>

          {inBattle ? (
            <div className="command-bar" style={{ flexWrap: 'wrap' }}>
              <Button type="primary" danger icon={<ThunderboltOutlined />} onClick={battleAttack}>攻击</Button>
              <Button icon={<MedicineBoxOutlined />} disabled>技能</Button>
              <Button icon={<MedicineBoxOutlined />} disabled>道具</Button>
              <Button onClick={battleEscape}>逃跑</Button>
            </div>
          ) : (
            <div className="command-bar" style={{ flexWrap: 'wrap', gap: 4 }}>
              <Space.Compact>
                <Button icon={<ArrowUpOutlined />} onClick={() => doMove('n')}>北</Button>
                <Button icon={<ArrowDownOutlined />} onClick={() => doMove('s')}>南</Button>
                <Button icon={<ArrowLeftOutlined />} onClick={() => doMove('w')}>西</Button>
                <Button icon={<ArrowRightOutlined />} onClick={() => doMove('e')}>东</Button>
              </Space.Compact>
              <Button type="primary" icon={<ThunderboltOutlined />} onClick={startBattle}>打怪</Button>
              <Button onClick={doHeal}>治疗(100金)</Button>
              <Input
                placeholder="输入指令/聊天..."
                value={cmdInput}
                onChange={(e) => setCmdInput(e.target.value)}
                onPressEnter={() => {
                  if (cmdInput.trim()) {
                    addMessage('chat', `你说: ${cmdInput}`)
                    if (ws) ws.send(JSON.stringify({ type: 'chat', channel: 'world', content: cmdInput }))
                    setCmdInput('')
                  }
                }}
                style={{ flex: 1, minWidth: 200 }}
              />
            </div>
          )}
        </div>

        <div className="side-panel">
          <Card size="small" title={<><UserOutlined /> 角色</>}>
            <Progress percent={expPct} size="small" strokeColor="#ffcc00" format={() => `EXP ${char?.exp}/${char?.next_exp}`} />
            <div style={{ marginTop: 8, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4, fontSize: 12 }}>
              <div>攻击: {char?.damage}</div>
              <div>防御: {char?.defense}</div>
              <div>速度: {char?.speed}</div>
              <div>法伤: {char?.magic_damage}</div>
              <div>属性点: {char?.attr_points}</div>
            </div>
          </Card>

          <Tabs
            size="small"
            items={[
              {
                key: 'map',
                label: <span><EnvironmentOutlined />地图</span>,
                children: (
                  <div style={{ fontSize: 13 }}>
                    <div style={{ marginBottom: 8 }}><b>{mapInfo?.name}</b></div>
                    <div>位置: ({char?.pos_x}, {char?.pos_y})</div>
                    <div style={{ marginTop: 8 }}>NPC:</div>
                    <List size="small" dataSource={mapInfo?.npcs || []} renderItem={(n: any) => (
                      <List.Item><Tag>{n.title}</Tag>{n.name}</List.Item>
                    )} />
                  </div>
                )
              },
              {
                key: 'bag',
                label: <span><ShoppingOutlined />背包</span>,
                children: (
                  <List size="small" dataSource={bag} renderItem={(it: any) => (
                    <List.Item
                      actions={[<a key="use" onClick={() => useItem(it)}>使用</a>]}
                    >
                      <List.Item.Meta title={`${it.name} x${it.count}`} description={it.type === 1 ? '装备' : it.type === 3 ? '药品' : '道具'} />
                    </List.Item>
                  )} />
                )
              },
              {
                key: 'quest',
                label: <span><SnippetsOutlined />任务</span>,
                children: (
                  <List size="small" dataSource={quests} renderItem={(q: any) => (
                    <List.Item>
                      <List.Item.Meta
                        title={q.name}
                        description={q.progress_text}
                      />
                    </List.Item>
                  )} />
                )
              },
              {
                key: 'team',
                label: <span><TeamOutlined />社交</span>,
                children: <div style={{ fontSize: 13 }}>组队和好友功能在二期UI版本完善</div>
              },
            ]}
          />

          <Card size="small" title="世界频道" style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 200 }} bodyStyle={{ flex: 1, padding: 8, overflow: 'hidden' }}>
            <div style={{ height: 140, overflowY: 'auto', fontSize: 12, marginBottom: 8 }}>
              {messages.filter(m => m.type === 'chat').slice(-20).map((m, i) => (
                <div key={i}>{m.text}</div>
              ))}
            </div>
            <Space.Compact style={{ width: '100%' }}>
              <Input size="small" value={chatInput} onChange={(e) => setChatInput(e.target.value)} onPressEnter={sendChat} placeholder="世界聊天" />
              <Button size="small" type="primary" icon={<SendOutlined />} onClick={sendChat} />
            </Space.Compact>
          </Card>
        </div>
      </div>
    </div>
  )
}
