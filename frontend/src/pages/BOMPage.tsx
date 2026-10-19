import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  FlaskConical, Plus, Trash2, Save, Edit2, ChevronRight,
  Package, AlertTriangle, CheckCircle, Calculator, DollarSign
} from 'lucide-react'
import { erpApi, posApi } from '../lib/api'
import { useBrand } from '../contexts/BrandContext'

interface BOMIngredient {
  raw_material_id: number
  raw_material_name: string
  raw_material_code: string
  unit: string
  quantity_per_batch: number
  unit_cost: number
  ingredient_cost: number
  current_stock: number
  is_sufficient_for_1_batch: boolean
}

interface BOMData {
  bom_id: number
  product_id: number
  batch_size: number
  wastage_percent: number
  labor_cost: number
  overhead_cost: number
  raw_material_cost: number
  total_batch_cost: number
  unit_cost: number
  ingredients: BOMIngredient[]
}

export default function BOMPage() {
  const { activeBrand } = useBrand()
  const queryClient = useQueryClient()
  const [selectedProduct, setSelectedProduct] = useState<any>(null)
  const [editMode, setEditMode] = useState(false)

  const { data: products = [] } = useQuery({
    queryKey: ['products', activeBrand.id],
    queryFn: () => posApi.products(activeBrand.id).then(r => r.data),
    enabled: activeBrand.id > 0,
  })

  const { data: rawMaterials = [] } = useQuery({
    queryKey: ['raw-materials'],
    queryFn: () => erpApi.rawMaterials().then(r => r.data),
  })

  const { data: bomData, isLoading: bomLoading } = useQuery({
    queryKey: ['bom', selectedProduct?.id],
    queryFn: () => erpApi.getBOM(selectedProduct!.id).then(r => r.data),
    enabled: !!selectedProduct?.id,
  })

  const totalRawCost = bomData?.ingredients?.reduce((s: number, i: BOMIngredient) => s + i.ingredient_cost, 0) || 0

  return (
    <div className="page-container">
      <div className="section-header">
        <div>
          <h1 className="section-title">🧪 Formula / BOM Builder</h1>
          <p className="text-sm text-slate-500">Bill of Materials & Recipe Management</p>
        </div>
        <button className="btn-primary">
          <Plus className="w-4 h-4" /> New Formula
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Product List */}
        <div className="card p-5">
          <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
            <Package className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />
            Products
          </h3>
          {activeBrand.id === 0 ? (
            <p className="text-xs text-slate-400 text-center py-6">Select a brand profile</p>
          ) : (
            <div className="space-y-2">
              {products.map((p: any) => (
                <button
                  key={p.id}
                  onClick={() => setSelectedProduct(p)}
                  className={`w-full flex items-center justify-between p-3 rounded-xl border text-left transition-all ${
                    selectedProduct?.id === p.id
                      ? 'border-[var(--brand-border)] shadow-brand'
                      : 'border-slate-100 hover:border-slate-200'
                  }`}
                  style={selectedProduct?.id === p.id ? { background: 'var(--brand-surface)' } : {}}
                >
                  <div>
                    <div className="text-sm font-semibold text-slate-800">{p.name}</div>
                    <div className="text-xs text-slate-400 mt-0.5">SKU: {p.sku} · {p.current_stock} {p.unit}</div>
                  </div>
                  <ChevronRight className="w-4 h-4 text-slate-400" />
                </button>
              ))}
              {products.length === 0 && (
                <p className="text-xs text-slate-400 text-center py-6">No products. Create products first.</p>
              )}
            </div>
          )}
        </div>

        {/* BOM Details */}
        <div className="lg:col-span-2">
          {!selectedProduct ? (
            <div className="card p-12 flex items-center justify-center">
              <div className="text-center">
                <FlaskConical className="w-12 h-12 text-slate-200 mx-auto mb-3" />
                <p className="text-slate-400 text-sm">Select a product to view its BOM</p>
              </div>
            </div>
          ) : bomLoading ? (
            <div className="card p-8 flex items-center justify-center">
              <div className="text-slate-400 text-sm">Loading BOM...</div>
            </div>
          ) : !bomData ? (
            <div className="card p-8 text-center">
              <FlaskConical className="w-10 h-10 text-slate-300 mx-auto mb-3" />
              <h3 className="font-semibold text-slate-600 mb-2">No BOM Found</h3>
              <p className="text-sm text-slate-400 mb-4">Create a Bill of Materials for {selectedProduct.name}</p>
              <button className="btn-primary mx-auto">
                <Plus className="w-4 h-4" /> Create BOM
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* BOM Header */}
              <div className="card p-5">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="font-bold text-slate-800 text-lg">{selectedProduct.name}</h3>
                    <p className="text-xs text-slate-400">BOM ID: {bomData.bom_id}</p>
                  </div>
                  <button onClick={() => setEditMode(!editMode)} className="btn-secondary">
                    <Edit2 className="w-3.5 h-3.5" />
                    {editMode ? 'View Mode' : 'Edit'}
                  </button>
                </div>

                <div className="grid grid-cols-4 gap-4">
                  {[
                    { label: 'Batch Size', value: `${bomData.batch_size} units`, icon: Package },
                    { label: 'Wastage %', value: `${bomData.wastage_percent}%`, icon: AlertTriangle },
                    { label: 'Labor Cost', value: `MMK ${bomData.labor_cost?.toLocaleString()}`, icon: DollarSign },
                    { label: 'Unit COGS', value: `MMK ${bomData.unit_cost?.toLocaleString()}`, icon: Calculator },
                  ].map(stat => (
                    <div key={stat.label} className="text-center p-3 rounded-xl" style={{ background: 'var(--brand-surface)' }}>
                      <stat.icon className="w-4 h-4 mx-auto mb-1" style={{ color: 'var(--brand-primary)' }} />
                      <div className="font-bold text-sm text-slate-800">{stat.value}</div>
                      <div className="text-xs text-slate-500">{stat.label}</div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Ingredients Table */}
              <div className="card">
                <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
                  <h3 className="font-semibold text-slate-700">Ingredients / Raw Materials</h3>
                  {editMode && (
                    <button className="btn-secondary text-xs py-1.5">
                      <Plus className="w-3.5 h-3.5" /> Add Ingredient
                    </button>
                  )}
                </div>
                <div className="table-wrapper rounded-none">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Ingredient</th>
                        <th>Code</th>
                        <th>Qty / Batch</th>
                        <th>Unit Cost</th>
                        <th>Batch Cost</th>
                        <th>Stock</th>
                        <th>Status</th>
                        {editMode && <th></th>}
                      </tr>
                    </thead>
                    <tbody>
                      {bomData.ingredients?.map((ing: BOMIngredient) => (
                        <tr key={ing.raw_material_id}>
                          <td className="font-medium text-slate-800">{ing.raw_material_name}</td>
                          <td><span className="badge bg-slate-100 text-slate-600">{ing.raw_material_code}</span></td>
                          <td>
                            {editMode ? (
                              <input
                                type="number"
                                defaultValue={ing.quantity_per_batch}
                                className="w-20 text-xs border border-slate-200 rounded-lg px-2 py-1 outline-none"
                              />
                            ) : (
                              <span>{ing.quantity_per_batch} {ing.unit}</span>
                            )}
                          </td>
                          <td className="font-mono text-slate-600">MMK {ing.unit_cost?.toLocaleString()}</td>
                          <td className="font-mono font-semibold" style={{ color: 'var(--brand-primary)' }}>
                            MMK {ing.ingredient_cost?.toLocaleString()}
                          </td>
                          <td className="text-slate-600">{ing.current_stock} {ing.unit}</td>
                          <td>
                            {ing.is_sufficient_for_1_batch ? (
                              <span className="badge bg-green-100 text-green-700 gap-1">
                                <CheckCircle className="w-3 h-3" /> OK
                              </span>
                            ) : (
                              <span className="badge bg-red-100 text-red-600 gap-1">
                                <AlertTriangle className="w-3 h-3" /> Low
                              </span>
                            )}
                          </td>
                          {editMode && (
                            <td>
                              <button className="p-1 rounded hover:bg-red-50 hover:text-red-500 text-slate-400">
                                <Trash2 className="w-3.5 h-3.5" />
                              </button>
                            </td>
                          )}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Cost Summary Footer */}
                <div className="px-5 py-4 border-t border-slate-100 bg-slate-50 grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-slate-500">Raw Material Cost</span>
                    <div className="font-bold text-slate-800">MMK {totalRawCost.toLocaleString()}</div>
                  </div>
                  <div>
                    <span className="text-slate-500">+ Labor + Overhead</span>
                    <div className="font-bold text-slate-800">
                      MMK {((bomData.labor_cost || 0) + (bomData.overhead_cost || 0)).toLocaleString()}
                    </div>
                  </div>
                  <div>
                    <span className="text-slate-500">Total Batch Cost</span>
                    <div className="font-bold text-lg" style={{ color: 'var(--brand-primary)' }}>
                      MMK {bomData.total_batch_cost?.toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>

              {editMode && (
                <div className="flex justify-end">
                  <button className="btn-primary">
                    <Save className="w-4 h-4" /> Save BOM Changes
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
