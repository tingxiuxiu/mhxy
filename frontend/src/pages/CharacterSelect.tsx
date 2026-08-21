import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card, Row, Col, Typography, message, Modal, Form, Input, Select, Empty } from 'antd'
import { UserAddOutlined, PlayCircleOutlined, LogoutOutlined } from '@ant-design/icons'
import api from '../api/client'
import { useGameStore } from '../store/game'

const { Title } = Typography

const JOB_OPTIONS = [
  { value: 1, label: '大唐官府' },
  { value: 2, label: '方寸山' },
  { value: 3, label: '化生寺' },
  { value: 4, label: '女儿村' },
  { value: 5, label: '天宫' },
  { value: 6, label: '龙宫' },
]

export default function CharacterSelect() {
  const nav = useNavigate()
  const [chars, setChars] = useState<any[]>([])
  const [modalOpen, setModalOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [form] = Form.useForm()
  const { logout } = useGameStore()

  const loadChars = async () => {
    try {
      const { data } = await api.get('/character/list')
      setChars(data)
    } catch (e: any) {
      if (e.response?.status === 401) nav('/login')
    }
  }

  useEffect(() => {
    loadChars()
  }, [])

  const enterGame = (c: any) => {
    localStorage.setItem('char_id', String(c.id))
    nav('/game')
  }

  const createChar = async (values: any) => {
    setLoading(true)
    try {
      await api.post('/character/create', values)
      message.success('创建成功')
      setModalOpen(false)
      form.resetFields()
      loadChars()
    } catch (e: any) {
      message.error(e.response?.data?.msg || '创建失败')
    } finally {
      setLoading(false)
    }
  }

  const doLogout = () => {
    logout()
    nav('/login')
  }

  return (
    <div style={{
      minHeight: '100vh', padding: 40,
      background: 'linear-gradient(135deg, #2c1810 0%, #4a2c1a 100%)'
    }}>
      <div style={{ maxWidth: 960, margin: '0 auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
          <Title level={2} style={{ color: '#f5e6c8', margin: 0 }}>选择角色</Title>
          <Button icon={<LogoutOutlined />} onClick={doLogout}>退出登录</Button>
        </div>

        {chars.length === 0 ? (
          <Card style={{ textAlign: 'center', padding: 40 }}>
            <Empty description="还没有角色，创建一个开始游戏吧！">
              <Button type="primary" icon={<UserAddOutlined />} onClick={() => setModalOpen(true)}>
                创建角色
              </Button>
            </Empty>
          </Card>
        ) : (
          <>
            <Row gutter={[16, 16]}>
              {chars.map((c) => (
                <Col xs={24} sm={12} md={8} key={c.id}>
                  <Card hoverable actions={[
                    <Button type="primary" icon={<PlayCircleOutlined />} onClick={() => enterGame(c)}>
                      进入游戏
                    </Button>
                  ]}>
                    <Card.Meta
                      title={c.name}
                      description={
                        <div>
                          <div>门派：{JOB_OPTIONS.find(j => j.value === c.job)?.label || '未知'}</div>
                          <div>等级：Lv.{c.level}</div>
                        </div>
                      }
                    />
                  </Card>
                </Col>
              ))}
            </Row>
            <div style={{ marginTop: 24, textAlign: 'center' }}>
              <Button icon={<UserAddOutlined />} onClick={() => setModalOpen(true)}>创建新角色</Button>
            </div>
          </>
        )}

        <Modal title="创建角色" open={modalOpen} onCancel={() => setModalOpen(false)} footer={null}>
          <Form form={form} onFinish={createChar} layout="vertical">
            <Form.Item name="name" label="角色名称" rules={[{ required: true, min: 2, max: 12, message: '名称2-12字' }]}>
              <Input placeholder="请输入角色名" />
            </Form.Item>
            <Form.Item name="job" label="选择门派" rules={[{ required: true, message: '请选择门派' }]}>
              <Select options={JOB_OPTIONS} placeholder="选择门派" />
            </Form.Item>
            <Form.Item>
              <Button type="primary" htmlType="submit" loading={loading} block>创建</Button>
            </Form.Item>
          </Form>
        </Modal>
      </div>
    </div>
  )
}
