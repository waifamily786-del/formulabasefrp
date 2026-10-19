import React, { useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Zap, LayoutDashboard, FileText, FlaskConical, Factory,
  BarChart3, Package, Users, Settings, LogOut, ChevronRight,
  Building2, Layers, Bell, Search
} from 'lucide-react'
import { NavLink, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { brandsApi } from '../lib/api'
import { useBrand, MASTER_BRAND } from '../contexts/BrandContext'
import { useAuth } from '../contexts/AuthContext'

const masterNavItems = [
  { icon: LayoutDashboard, label: 'Master Dashboard', to: '/' },
  { icon: Package, label: 'Raw Materials', to: '/raw-materials' },
  { icon: Factory, label: 'Production Batches', to: '/production' },
  { icon: BarChart3, label: 'Financial Reports', to: '/financials' },
  { icon: Layers, label: 'Chart of Accounts', to: '/coa' },
]

const brandNavItems = [
  { icon: LayoutDashboard, label: 'Brand Dashboard', to: '/' },
  { icon: FileText, label: 'Quick Invoice', to: '/invoice' },
  { icon: Users, label: 'Customers', to: '/customers' },
  { icon: Package, label: 'Products', to: '/products' },
  { icon: FlaskConical, label: 'Formula / BOM', to: '/bom' },
  { icon: Factory, label: 'Batch Simulator', to: '/production' },
  { icon: BarChart3, label: 'Financial Reports', to: '/financials' },
  { icon: FileText, label: 'Invoices', to: '/invoices' },
]

export default function Sidebar() {
  const { activeBrand, brands, setBrands, switchBrand } = useBrand()
  const { user, logout } = useAuth()
  const location = useLocation()
  const isMaster = activeBrand.id === 0

  const { data: brandsData } = useQuery({
    queryKey: ['brands'],
    queryFn: () => brandsApi.list().then(r => r.data),
  })

  useEffect(() => {
    if (brandsData) setBrands(brandsData)
  }, [brandsData, setBrands])

  const navItems = isMaster ? masterNavItems : brandNavItems

  return (
    <div className="flex flex-col h-full w-64 bg-white border-r border-slate-100 sidebar-transition">
      {/* Brand Switcher Header */}
      <div className="p-4 border-b border-slate-100">
        {/* Master ERP button */}
        <button
          onClick={() => switchBrand(MASTER_BRAND)}
          className={`w-full flex items-center gap-3 p-3 rounded-xl mb-3 transition-all duration-200 ${
            isMaster ? 'shadow-brand' : 'hover:bg-slate-50'
          }`}
          style={isMaster ? {
            background: 'linear-gradient(135deg, #1E3A8A, #2563EB)',
          } : {}}
        >
          <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 ${
            isMaster ? 'bg-white/20' : 'bg-blue-100'
          }`}>
            <Zap className={`w-5 h-5 ${isMaster ? 'text-white' : 'text-blue-600'}`} />
          </div>
          <div className="text-left min-w-0">
            <div className={`text-xs font-bold truncate ${isMaster ? 'text-white' : 'text-slate-800'}`}>
              Formula Base ERP
            </div>
            <div className={`text-xs truncate ${isMaster ? 'text-blue-200' : 'text-slate-400'}`}>
              Master Control
            </div>
          </div>
          {isMaster && <Building2 className="w-4 h-4 text-white/70 ml-auto flex-shrink-0" />}
        </button>

        {/* Brand Profile Cards */}
        <div className="space-y-1.5">
          <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-1 mb-2">
            Brand Profiles
          </p>
          {brands.map(brand => {
            const isActive = activeBrand.id === brand.id
            return (
              <motion.button
                key={brand.id}
                onClick={() => switchBrand(brand)}
                whileTap={{ scale: 0.98 }}
                className="w-full flex items-center gap-3 p-2.5 rounded-xl transition-all duration-200"
                style={isActive ? {
                  background: `linear-gradient(135deg, ${brand.theme_gradient_start}, ${brand.theme_gradient_mid})`,
                } : { background: 'transparent' }}
              >
                <div
                  className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 text-xs font-bold"
                  style={isActive ? { background: 'rgba(255,255,255,0.2)', color: 'white' } : {
                    background: brand.theme_surface_tint,
                    color: brand.theme_primary_color,
                  }}
                >
                  {brand.name.substring(0, 2).toUpperCase()}
                </div>
                <div className="text-left min-w-0 flex-1">
                  <div className={`text-xs font-bold truncate ${isActive ? 'text-white' : 'text-slate-700'}`}>
                    {brand.name}
                  </div>
                  <div className={`text-xs truncate ${isActive ? 'text-white/70' : 'text-slate-400'}`}>
                    {brand.full_name || brand.tagline || 'Brand Profile'}
                  </div>
                </div>
                {isActive && <ChevronRight className="w-3 h-3 text-white/70 flex-shrink-0" />}
              </motion.button>
            )
          })}

          {brands.length === 0 && (
            <div className="text-xs text-slate-400 text-center py-2 px-3 bg-slate-50 rounded-lg">
              No brands configured yet
            </div>
          )}
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
        <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 mb-3">
          {isMaster ? 'Master ERP' : activeBrand.name + ' Menu'}
        </p>
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
            style={({ isActive }) => isActive ? {
              color: 'var(--brand-primary)',
              background: 'var(--brand-surface)',
            } : {}}
          >
            <item.icon className="w-4 h-4 flex-shrink-0" />
            <span>{item.label}</span>
          </NavLink>
        ))}

        <div className="pt-3 border-t border-slate-100 mt-3">
          <NavLink
            to="/settings"
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
          >
            <Settings className="w-4 h-4 flex-shrink-0" />
            <span>Settings</span>
          </NavLink>
        </div>
      </nav>

      {/* User Footer */}
      <div className="p-4 border-t border-slate-100">
        <div className="flex items-center gap-3 p-3 rounded-xl bg-slate-50">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white flex-shrink-0"
            style={{ background: 'var(--brand-primary)' }}>
            {user?.full_name?.[0] || 'A'}
          </div>
          <div className="min-w-0 flex-1">
            <div className="text-xs font-semibold text-slate-700 truncate">{user?.full_name}</div>
            <div className="text-xs text-slate-400 truncate capitalize">{user?.role?.toLowerCase()}</div>
          </div>
          <button
            onClick={logout}
            className="p-1.5 rounded-lg hover:bg-red-50 hover:text-red-500 text-slate-400 transition-colors"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </div>
  )
}
