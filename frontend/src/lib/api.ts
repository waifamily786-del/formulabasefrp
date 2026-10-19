import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Attach auth token from localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Redirect to login on 401
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('auth_token')
      localStorage.removeItem('auth_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default api

// ─── Auth ─────────────────────────────────────────────────────────
export const authApi = {
  login: (username: string, password: string) =>
    api.post('/auth/login', { username, password }),
  me: () => api.get('/auth/me'),
}

// ─── Brands ───────────────────────────────────────────────────────
export const brandsApi = {
  list: () => api.get('/brands/'),
  get: (id: number) => api.get(`/brands/${id}`),
  create: (data: Record<string, unknown>) => api.post('/brands/', data),
  update: (id: number, data: Record<string, unknown>) => api.put(`/brands/${id}`, data),
  updateTheme: (id: number, theme: Record<string, string>) => api.put(`/brands/${id}/theme`, theme),
  uploadTemplate: (id: number, file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    return api.post(`/brands/${id}/upload-template`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  getTemplateMapping: (id: number) => api.get(`/brands/${id}/template-mapping`),
  updateTemplateMapping: (id: number, mapping: Record<string, unknown>) =>
    api.put(`/brands/${id}/template-mapping`, mapping),
}

// ─── ERP / Formula ────────────────────────────────────────────────
export const erpApi = {
  rawMaterials: () => api.get('/erp/raw-materials'),
  createRawMaterial: (data: Record<string, unknown>) => api.post('/erp/raw-materials', data),
  getBOM: (productId: number) => api.get(`/erp/bom/${productId}`),
  simulateProduction: (productId: number, qty: number) =>
    api.get(`/erp/simulate-production/${productId}`, { params: { desired_qty: qty } }),
  executeProductionBatch: (data: Record<string, unknown>) => api.post('/erp/production-batches', data),
  productionBatches: (brandId?: number) =>
    api.get('/erp/production-batches', brandId ? { params: { brand_id: brandId } } : undefined),
  inventorySummary: () => api.get('/erp/inventory/summary'),
}

// ─── POS ──────────────────────────────────────────────────────────
export const posApi = {
  customers: (brandId: number) => api.get(`/pos/customers/${brandId}`),
  createCustomer: (brandId: number, data: Record<string, unknown>) =>
    api.post(`/pos/customers/${brandId}`, data),
  products: (brandId: number) => api.get(`/pos/products/${brandId}`),
  createInvoice: (data: Record<string, unknown>) => api.post('/pos/invoices', data),
  invoices: (brandId: number, limit = 50) =>
    api.get(`/pos/invoices/${brandId}`, { params: { limit } }),
  invoiceDetail: (id: number) => api.get(`/pos/invoices/detail/${id}`),
  dashboard: (brandId: number) => api.get(`/pos/dashboard/${brandId}`),
}

// ─── Accounting ───────────────────────────────────────────────────
export const accountingApi = {
  incomeStatement: (startDate: string, endDate: string, brandId?: number) =>
    api.get('/accounting/income-statement', {
      params: { start_date: startDate, end_date: endDate, brand_id: brandId },
    }),
  balanceSheet: (asOfDate: string) =>
    api.get('/accounting/balance-sheet', { params: { as_of_date: asOfDate } }),
  arAging: () => api.get('/accounting/ar-aging'),
  journalEntries: (brandId?: number, limit = 50) =>
    api.get('/accounting/journal-entries', { params: { brand_id: brandId, limit } }),
  expenses: (brandId?: number) =>
    api.get('/accounting/expenses', { params: { brand_id: brandId } }),
  createExpense: (data: Record<string, unknown>) => api.post('/accounting/expenses', data),
  summary: () => api.get('/accounting/summary'),
  chartOfAccounts: () => api.get('/accounting/chart-of-accounts'),
}

// ─── PDF Engine ───────────────────────────────────────────────────
export const pdfApi = {
  downloadInvoice: (invoiceId: number) =>
    api.get(`/pdf/invoice/${invoiceId}`, { responseType: 'blob' }),
}
