import apiClient from './client'

/**
 * AUTHENTICATION
 * 
 * Refresh token is handled via HttpOnly cookie — never sent in request body.
 * CSRF token is handled automatically by the client interceptor.
 */
export const authApi = {
  login: (email, password) => apiClient.post('/auth/login', { email, password }),
  logout: () => apiClient.post('/auth/logout'),
  refresh: () => apiClient.post('/auth/refresh'),  // cookie-based, no body
  me: () => apiClient.get('/auth/me'),
  changePassword: (current_password, new_password) => 
    apiClient.post('/auth/change-password', { current_password, new_password }),
  
  // MFA
  mfaSetup: () => apiClient.post('/auth/mfa/setup'),
  mfaVerify: (otp_code) => apiClient.post('/auth/mfa/verify', { otp_code }),
  mfaLoginVerify: (user_id, otp_code) => 
    apiClient.post('/auth/mfa/login-verify', { user_id, otp_code }),
  mfaDisable: (user_id) => apiClient.post('/auth/mfa/disable', { user_id }),
}

/**
 * ORDERS
 */
export const ordersApi = {
  list: (params) => apiClient.get('/orders', { params }), // ?page=1&limit=10&status=ACTIVE
  create: (data) => apiClient.post('/orders', data),
  createWithNewCustomer: (data) => apiClient.post('/orders/with-new-customer', data),
  getById: (orderId) => apiClient.get(`/orders/${orderId}`),
  update: (orderId, data) => apiClient.patch(`/orders/${orderId}`, data),
  getTimeline: (orderId) => apiClient.get(`/orders/${orderId}/timeline`),
  getDashboardStats: () => apiClient.get('/orders/dashboard/stats'),
}

/**
 * MILESTONES
 */
export const milestonesApi = {
  listByOrder: (orderId) => apiClient.get(`/orders/${orderId}/milestones`),
  create: (orderId, data) => apiClient.post(`/orders/${orderId}/milestones`, data),
  update: (milestoneId, data) => apiClient.patch(`/milestones/${milestoneId}`, data), // { status, remarks }
  completeStage: (orderId) => apiClient.post(`/orders/${orderId}/complete-stage`),
}

/**
 * UPLOADS & MEDIA
 * 
 * Upload Integration Example:
 * 
 * const handlePhotoUpload = async (file, orderId) => {
 *    try {
 *      setLoading(true)
 *      await uploadsApi.uploadPhoto(file, orderId, 'QA_IMAGE')
 *      toast.success('Photo uploaded!')
 *    } catch (err) {
 *      toast.error('Upload failed')
 *    } finally {
 *      setLoading(false)
 *    }
 * }
 */
export const uploadsApi = {
  uploadPhoto: (file, orderId, category) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('order_id', orderId)
    formData.append('media_type', category)
    
    return apiClient.post('/upload/photo', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  
  uploadDocument: (file, orderId, docType) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('order_id', orderId)
    formData.append('document_type', docType)
    
    return apiClient.post('/upload/document', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  listMediaByOrder: (orderId) => apiClient.get(`/orders/${orderId}/media`),
  deleteMedia: (fileId) => apiClient.delete(`/media/${fileId}`),
  getDocumentChecklist: (orderId) => apiClient.get(`/orders/${orderId}/document-checklist`),
}

/**
 * DOCUMENTS
 */
export const documentsApi = {
  vault: () => apiClient.get('/documents/vault'),
  listByOrder: (orderId) => apiClient.get(`/orders/${orderId}/documents`),
  delete: (docId) => apiClient.delete(`/documents/${docId}`),
  approve: (docId) => apiClient.post(`/documents/${docId}/approve`),
  reject: (docId, remarks) => apiClient.post(`/documents/${docId}/reject`, { remarks }),
  
  // Custom helper for secure downloads (assumes backend handles redirect or streaming)
  download: (docId) => apiClient.get(`/documents/${docId}/download`, {
    responseType: 'blob' 
  }),
}

/**
 * NOTIFICATIONS
 */
export const notificationsApi = {
  list: (params) => apiClient.get('/notifications', { params }),
  markAsRead: (id) => apiClient.post(`/notifications/${id}/read`),
  markAllRead: () => apiClient.post('/notifications/read-all'),
}

/**
 * CUSTOMERS
 */
export const customersApi = {
  list: (params) => apiClient.get('/customers', { params }),
  create: (data) => apiClient.post('/customers', data),
  getById: (id) => apiClient.get(`/customers/${id}`),
}
