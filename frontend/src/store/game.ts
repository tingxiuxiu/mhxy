import { create } from 'zustand'

interface CharInfo {
  id: number
  name: string
  level: number
  job: number
  hp: number
  mp: number
  hp_max: number
  mp_max: number
  cash: number
  exp: number
  next_exp: number
  map_id: number
  pos_x: number
  pos_y: number
}

interface GameState {
  char: CharInfo | null
  messages: Array<{ type: string; text: string; time: number }>
  inBattle: boolean
  battleState: any
  setChar: (c: CharInfo | null) => void
  addMessage: (type: string, text: string) => void
  setBattle: (inBattle: boolean, state?: any) => void
  logout: () => void
}

export const useGameStore = create<GameState>((set, get) => ({
  char: null,
  messages: [],
  inBattle: false,
  battleState: null,
  setChar: (c) => set({ char: c }),
  addMessage: (type, text) => {
    const msgs = [...get().messages, { type, text, time: Date.now() }]
    if (msgs.length > 200) msgs.shift()
    set({ messages: msgs })
  },
  setBattle: (inBattle, state) => set({ inBattle, battleState: state || null }),
  logout: () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('char_id')
    set({ char: null, messages: [], inBattle: false })
  },
}))
