import request from '@/utils/request'

export const systemCheck=async()=>{
  return await request.get('/api/sys_health')
}
