import React, { useEffect, useState } from 'react'
import { Card, Button, Space, Tag, Table, Modal, DatePicker, message } from 'antd'
import { DeleteOutlined, EditOutlined, PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons'
import { 
  getScheduledTasks, 
  toggleScheduledTask, 
  updateScheduleTime, 
  deleteScheduledTask,
  ScheduledTask
} from '@/services/scheduledTask'

const ScheduledTasksPage: React.FC = () => {
  const [tasks, setTasks] = useState<ScheduledTask[]>([])
  const [loading, setLoading] = useState(false)
  const [editModalVisible, setEditModalVisible] = useState(false)
  const [editingTask, setEditingTask] = useState<ScheduledTask | null>(null)
  const [newScheduleTime, setNewScheduleTime] = useState<string>('')

  useEffect(() => {
    loadTasks()
  }, [])

  const loadTasks = async () => {
    setLoading(true)
    try {
      const response = await getScheduledTasks()
      setTasks(response.data || [])
    } catch (error) {
      message.error('加载定时任务失败')
    } finally {
      setLoading(false)
    }
  }

  const handleToggleTask = async (taskId: number, enabled: boolean) => {
    try {
      await toggleScheduledTask(taskId, enabled)
      message.success(`任务已${enabled ? '启用' : '禁用'}`)
      loadTasks()
    } catch (error) {
      message.error('操作失败')
    }
  }

  const handleDeleteTask = async (taskId: number) => {
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个定时任务吗？',
      onOk: async () => {
        try {
          await deleteScheduledTask(taskId)
          message.success('任务删除成功')
          loadTasks()
        } catch (error) {
          message.error('删除失败')
        }
      }
    })
  }

  const handleEditScheduleTime = (task: ScheduledTask) => {
    setEditingTask(task)
    setNewScheduleTime(task.schedule_time)
    setEditModalVisible(true)
  }

  const handleUpdateScheduleTime = async () => {
    if (!editingTask || !newScheduleTime) return

    try {
      await updateScheduleTime(editingTask.id, newScheduleTime)
      message.success('定时时间更新成功')
      setEditModalVisible(false)
      loadTasks()
    } catch (error) {
      message.error('更新失败')
    }
  }

  const getStatusTag = (status: string) => {
    const statusConfig = {
      pending: { color: 'blue', text: '等待中' },
      running: { color: 'orange', text: '执行中' },
      completed: { color: 'green', text: '已完成' },
      failed: { color: 'red', text: '失败' },
      cancelled: { color: 'gray', text: '已取消' }
    }
    const config = statusConfig[status as keyof typeof statusConfig] || { color: 'default', text: status }
    return <Tag color={config.color}>{config.text}</Tag>
  }

  const columns = [
    {
      title: '任务名称',
      dataIndex: 'task_name',
      key: 'task_name',
    },
    {
      title: '视频平台',
      dataIndex: 'platform',
      key: 'platform',
      render: (platform: string) => platform.toUpperCase()
    },
    {
      title: '定时时间',
      dataIndex: 'schedule_time',
      key: 'schedule_time',
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '下次执行',
      dataIndex: 'next_run_time',
      key: 'next_run_time',
      render: (time: string) => time ? new Date(time).toLocaleString() : '-'
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: getStatusTag
    },
    {
      title: '启用状态',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean) => (
        <Tag color={enabled ? 'success' : 'default'}>
          {enabled ? '已启用' : '已禁用'}
        </Tag>
      )
    },
    {
      title: '执行次数',
      dataIndex: 'run_count',
      key: 'run_count',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (time: string) => new Date(time).toLocaleString()
    },
    {
      title: '操作',
      key: 'action',
      render: (_: any, record: ScheduledTask) => (
        <Space size="middle">
          <Button
            size="small"
            icon={record.enabled ? <PauseCircleOutlined /> : <PlayCircleOutlined />}
            onClick={() => handleToggleTask(record.id, !record.enabled)}
          >
            {record.enabled ? '禁用' : '启用'}
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEditScheduleTime(record)}
            disabled={!record.enabled}
          >
            编辑时间
          </Button>
          <Button
            size="small"
            danger
            icon={<DeleteOutlined />}
            onClick={() => handleDeleteTask(record.id)}
          >
            删除
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div className="p-6">
      <Card 
        title="定时任务管理" 
        extra={
          <Button type="primary" onClick={loadTasks} loading={loading}>
            刷新
          </Button>
        }
      >
        <Table
          columns={columns}
          dataSource={tasks}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total) => `共 ${total} 条记录`
          }}
        />
      </Card>

      <Modal
        title="修改定时时间"
        open={editModalVisible}
        onOk={handleUpdateScheduleTime}
        onCancel={() => setEditModalVisible(false)}
        okText="确认"
        cancelText="取消"
      >
        <div className="py-4">
          <label className="block text-sm font-medium mb-2">新的定时时间：</label>
          <input
            type="datetime-local"
            value={newScheduleTime ? new Date(newScheduleTime).toISOString().slice(0, 16) : ''}
            onChange={(e) => setNewScheduleTime(e.target.value)}
            min={new Date(Date.now() + 60000).toISOString().slice(0, 16)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </Modal>
    </div>
  )
}

export default ScheduledTasksPage