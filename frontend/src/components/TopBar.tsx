import React from 'react'
import { Bell, Search, RefreshCw } from 'lucide-react'
import { useBrand } from '../contexts/BrandContext'
import { useQueryClient } from '@tanstack/react-query'

export default function TopBar() {
  const { activeBrand } = useBrand()
  const queryClient = useQueryClient()
  const isMaster = activeBrand.id === 0

  return (
    <header className="h-14 flex items-center justify-between px-6 bg-white border-b border-slate-100 flex-shrink-0">
      {/* Brand indicator */}
      <div className="flex items-center gap-3">
        <div
          className="h-6 w-1 rounded-full"
          style={{ background: 'var(--brand-primary)' }}
        />
        <div>
          <span className="text-sm font-bold text-slate-800">
            {isMaster ? 'Formula Base Master ERP' : activeBrand.full_name || activeBrand.name}
          </span>
          {!isMaster && activeBrand.tagline && (
            <span className="ml-2 text-xs text-slate-400">{activeBrand.tagline}</span>
          )}
        </div>
        {!isMaster && (
          <span
            className="px-2 py-0.5 rounded-full text-xs font-bold"
            style={{ background: 'var(--brand-surface)', color: 'var(--brand-primary)' }}
          >
            {activeBrand.name}
          </span>
        )}
      </div>

      {/* Right side */}
      <div className="flex items-center gap-2">
        <div className="relative hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Quick search..."
            className="pl-9 pr-4 py-1.5 text-xs rounded-lg border border-slate-200 bg-slate-50 text-slate-700 outline-none focus:border-[var(--brand-primary)] w-44 transition-all focus:w-56 focus:bg-white"
          />
        </div>

        <button
          onClick={() => queryClient.invalidateQueries()}
          className="p-2 rounded-lg hover:bg-slate-100 text-slate-500 transition-colors"
          title="Refresh data"
        >
          <RefreshCw className="w-4 h-4" />
        </button>

        <button className="relative p-2 rounded-lg hover:bg-slate-100 text-slate-500 transition-colors">
          <Bell className="w-4 h-4" />
          <span
            className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full"
            style={{ background: 'var(--brand-primary)' }}
          />
        </button>
      </div>
    </header>
  )
}
