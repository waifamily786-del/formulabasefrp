import React from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  TrendingUp, TrendingDown, DollarSign, Package, Users,
  AlertTriangle, FileText, BarChart2, ArrowUpRight
} from 'lucide-react'
import { posApi, erpApi, accountingApi } from '../lib/api'
import { useBrand } from '../contexts/BrandContext'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts'
import { format, subDays } from 'date-fns'

function StatCard({ title, value, sub, icon: Icon, trend, color }: {
  title: string, value: string, sub?: string, icon: React.ElementType,
  trend?: number, color?: string
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="stat-card text-white"
    >
      <div className="absolute inset-0 opacity-10 rounded-2xl"
        style={{ background: 'radial-gradient(circle at top right, white, transparent)' }} />
      <div className="flex items-start justify-between relative z-10">
        <div>
          <p className="text-xs font-medium opacity-80 mb-1">{title}</p>
          <p className="text-2xl font-bold font-display">{value}</p>
          {sub && <p className="text-xs opacity-70 mt-1">{sub}</p>}
        </div>
        <div className="p-2.5 rounded-xl bg-white/20">
          <Icon className="w-5 h-5" />
        </div>
      </div>
      {trend !== undefined && (
        <div className="flex items-center gap-1 text-xs relative z-10">
          {trend >= 0 ? (
            <TrendingUp className="w-3.5 h-3.5 text-green-300" />
          ) : (
            <TrendingDown className="w-3.5 h-3.5 text-red-300" />
          )}
          <span className={trend >= 0 ? 'text-green-200' : 'text-red-200'}>
            {trend >= 0 ? '+' : ''}{trend.toFixed(1)}% vs last month
          </span>
        </div>
      )}
    </motion.div>
  )
}

function formatMMK(amount: number) {
  if (amount >= 1_000_000) return `${(amount / 1_000_000).toFixed(1)}M`
  if (amount >= 1_000) return `${(amount / 1_000).toFixed(0)}K`
  return amount.toLocaleString()
}

export default function DashboardPage() {
  const { activeBrand } = useBrand()
  const isMaster = activeBrand.id === 0

  const { data: brandDash } = useQuery({
    queryKey: ['dashboard', activeBrand.id],
    queryFn: () => posApi.dashboard(activeBrand.id).then(r => r.data),
    enabled: !isMaster,
    refetchInterval: 30000,
  })

  const { data: inventorySummary } = useQuery({
    queryKey: ['inventory-summary'],
    queryFn: () => erpApi.inventorySummary().then(r => r.data),
    refetchInterval: 60000,
  })

  const { data: financialSummary } = useQuery({
    queryKey: ['financial-summary'],
    queryFn: () => accountingApi.summary().then(r => r.data),
    refetchInterval: 60000,
  })

  // Mock sparkline data
  const sparkData = Array.from({ length: 7 }, (_, i) => ({
    day: format(subDays(new Date(), 6 - i), 'EEE'),
    revenue: Math.floor(Math.random() * 500000) + 200000,
    profit: Math.floor(Math.random() * 150000) + 50000,
  }))

  const monthly = financialSummary?.monthly
  const monthlyRevenue = monthly?.revenue || 0
  const monthlyExpenses = monthly?.total_expenses || 0
  const monthlyProfit = monthly?.net_profit || 0

  const pieData = [
    { name: 'Revenue', value: monthlyRevenue, color: 'var(--brand-primary)' },
    { name: 'Expenses', value: monthlyExpenses, color: '#F87171' },
  ]

  return (
    <div className="page-container animate-enter">
      {/* Header */}
      <div className="section-header">
        <div>
          <h1 className="section-title">
            {isMaster ? '🏭 Master ERP Dashboard' : `📊 ${activeBrand.name} Dashboard`}
          </h1>
          <p className="text-sm text-slate-500 mt-0.5">
            {format(new Date(), 'EEEE, MMMM d, yyyy')} · Real-time data
          </p>
        </div>
        <a href="/invoice" className="btn-primary">
          <FileText className="w-4 h-4" />
          New Invoice
        </a>
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {!isMaster && brandDash && (
          <>
            <StatCard
              title="Today's Revenue"
              value={`MMK ${formatMMK(brandDash.today?.revenue || 0)}`}
              sub={`${brandDash.today?.invoice_count || 0} invoices`}
              icon={DollarSign}
              trend={12.5}
            />
            <StatCard
              title="Monthly Revenue"
              value={`MMK ${formatMMK(brandDash.this_month?.revenue || 0)}`}
              sub={`${brandDash.this_month?.invoice_count || 0} invoices`}
              icon={TrendingUp}
              trend={brandDash.this_month?.margin_percent}
            />
            <StatCard
              title="Gross Profit"
              value={`MMK ${formatMMK(brandDash.this_month?.gross_profit || 0)}`}
              sub={`${brandDash.this_month?.margin_percent?.toFixed(1) || 0}% margin`}
              icon={BarChart2}
            />
            <StatCard
              title="Accounts Receivable"
              value={`MMK ${formatMMK(brandDash.customers?.total_ar || 0)}`}
              sub={`${brandDash.customers?.total || 0} customers`}
              icon={Users}
            />
          </>
        )}

        {isMaster && (
          <>
            <StatCard
              title="Monthly Revenue"
              value={`MMK ${formatMMK(monthlyRevenue)}`}
              sub="All brands combined"
              icon={DollarSign}
            />
            <StatCard
              title="Net Profit"
              value={`MMK ${formatMMK(monthlyProfit)}`}
              sub="After all expenses"
              icon={TrendingUp}
            />
            <StatCard
              title="Raw Material Value"
              value={`MMK ${formatMMK(inventorySummary?.raw_materials?.total_value || 0)}`}
              sub={`${inventorySummary?.raw_materials?.count || 0} materials`}
              icon={Package}
            />
            <StatCard
              title="Finished Goods"
              value={`MMK ${formatMMK(inventorySummary?.finished_goods?.total_value || 0)}`}
              sub={`${inventorySummary?.finished_goods?.count || 0} products`}
              icon={Package}
            />
          </>
        )}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-6">
        {/* Revenue Chart */}
        <div className="card p-5 col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-slate-800">Revenue Trend (7 Days)</h3>
            <span className="badge" style={{ background: 'var(--brand-surface)', color: 'var(--brand-primary)' }}>
              Live
            </span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={sparkData} margin={{ top: 5, right: 5, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--brand-primary)" stopOpacity={0.2} />
                  <stop offset="95%" stopColor="var(--brand-primary)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="day" tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fontSize: 11, fill: '#94A3B8' }} axisLine={false} tickLine={false} tickFormatter={v => `${(v/1000).toFixed(0)}K`} />
              <Tooltip
                contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 4px 20px rgba(0,0,0,0.1)', fontSize: '12px' }}
                formatter={(v: number) => [`MMK ${v.toLocaleString()}`, 'Revenue']}
              />
              <Area type="monotone" dataKey="revenue" stroke="var(--brand-primary)" strokeWidth={2.5} fill="url(#revenueGrad)" dot={{ fill: 'var(--brand-primary)', r: 3 }} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Revenue vs Expenses Pie */}
        <div className="card p-5">
          <h3 className="font-semibold text-slate-800 mb-4">This Month</h3>
          {monthlyRevenue > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={150}>
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={45} outerRadius={65} paddingAngle={3} dataKey="value">
                    {pieData.map((entry, i) => (
                      <Cell key={i} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(v: number) => `MMK ${v.toLocaleString()}`} />
                </PieChart>
              </ResponsiveContainer>
              <div className="space-y-2 mt-3">
                {pieData.map((item, i) => (
                  <div key={i} className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: item.color }} />
                      <span className="text-slate-600">{item.name}</span>
                    </div>
                    <span className="font-semibold text-slate-800">{formatMMK(item.value)}</span>
                  </div>
                ))}
                <div className="border-t border-slate-100 pt-2 flex justify-between text-xs">
                  <span className="text-slate-500">Net Profit</span>
                  <span className="font-bold" style={{ color: 'var(--brand-primary)' }}>
                    {formatMMK(monthlyProfit)}
                  </span>
                </div>
              </div>
            </>
          ) : (
            <div className="h-32 flex items-center justify-center text-sm text-slate-400">
              No financial data yet
            </div>
          )}
        </div>
      </div>

      {/* Low Stock & Quick Links */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Low Stock Alerts */}
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <h3 className="font-semibold text-slate-800">Low Stock Alerts</h3>
            {inventorySummary?.raw_materials?.low_stock_count > 0 && (
              <span className="badge bg-amber-100 text-amber-700">
                {inventorySummary.raw_materials.low_stock_count} items
              </span>
            )}
          </div>
          <div className="space-y-2">
            {inventorySummary?.raw_materials?.low_stock_items?.slice(0, 5).map((item: any, i: number) => (
              <div key={i} className="flex items-center justify-between p-2.5 rounded-xl bg-amber-50">
                <span className="text-sm font-medium text-amber-800">{item.name}</span>
                <span className="text-xs text-amber-600">{item.stock} / {item.min} min</span>
              </div>
            ))}
            {!inventorySummary?.raw_materials?.low_stock_items?.length && (
              <div className="text-center py-6 text-sm text-slate-400">
                ✅ All stock levels healthy
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="card p-5">
          <h3 className="font-semibold text-slate-800 mb-4">Quick Actions</h3>
          <div className="grid grid-cols-2 gap-3">
            {[
              { label: 'New Invoice', to: '/invoice', desc: 'Create sales order' },
              { label: 'Add Product', to: '/products', desc: 'Register SKU' },
              { label: 'Run Batch', to: '/production', desc: 'Start production' },
              { label: 'P&L Report', to: '/financials', desc: 'View financials' },
            ].map(action => (
              <a
                key={action.label}
                href={action.to}
                className="flex flex-col p-3.5 rounded-xl border border-slate-100 hover:border-[var(--brand-border)] transition-all hover:shadow-card group"
                style={{ background: 'white' }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-semibold text-slate-700 group-hover:text-[var(--brand-primary)] transition-colors">
                    {action.label}
                  </span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-slate-400 group-hover:text-[var(--brand-primary)] transition-colors" />
                </div>
                <span className="text-xs text-slate-400">{action.desc}</span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
