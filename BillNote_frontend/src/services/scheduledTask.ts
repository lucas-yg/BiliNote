import { request } from '@/utils/request'

export interface ScheduledTaskRequest {
  task_name: string
  video_url: string
  platform: string
  schedule_time: string
  repeat_type?: string
  enabled?: boolean
  quality: string
  screenshot?: boolean
  link?: boolean
  model_name: string
  provider_id: string
  format?: string[]
  style?: string
  extras?: string
  video_understanding?: boolean
  video_interval?: number
  grid_size?: number[]
}

export interface ScheduledTask {
  id: number
  task_name: string
  video_url: string
  platform: string
  schedule_time: string
  next_run_time?: string
  repeat_type: string
  enabled: boolean
  status: string
  run_count: number
  last_run_time?: string
  last_task_id?: string
  error_message?: string
  created_at: string
  task_config: any
}

export const createScheduledTask = async (data: ScheduledTaskRequest) => {
  return request.post('/api/scheduled_tasks', data)
}

export const getScheduledTasks = async (enabledOnly = false) => {
  return request.get(`/api/scheduled_tasks?enabled_only=${enabledOnly}`)
}

export const getScheduledTask = async (taskId: number) => {
  return request.get(`/api/scheduled_tasks/${taskId}`)
}

export const toggleScheduledTask = async (taskId: number, enabled: boolean) => {
  return request.put(`/api/scheduled_tasks/${taskId}/toggle`, { enabled })
}

export const updateScheduleTime = async (taskId: number, scheduleTime: string) => {
  return request.put(`/api/scheduled_tasks/${taskId}/schedule_time`, { 
    schedule_time: scheduleTime 
  })
}

export const deleteScheduledTask = async (taskId: number) => {
  return request.delete(`/api/scheduled_tasks/${taskId}`)
}