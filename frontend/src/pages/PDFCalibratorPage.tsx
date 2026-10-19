import React, { useState, useRef, useCallback } from 'react'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Upload, Move, Save, Eye, Grid, Tag, AlertCircle,
  Plus, Trash2, RefreshCw, Info, Crosshair
} from 'lucide-react'
import { brandsApi } from '../lib/api'
import { useBrand } from '../contexts/BrandContext'

const FIELD_TAGS = [
  { tag: 'INVOICE_NO', label: 'Invoice Number', color: '#3B82F6' },
  { tag: 'DATE', label: 'Date', color: '#8B5CF6' },
  { tag: 'CUST_NAME', label: 'Customer Name', color: '#059669' },
  { tag: 'CUST_PHONE', label: 'Customer Phone', color: '#059669' },
  { tag: 'CUST_ADDRESS', label: 'Customer Address', color: '#059669' },
  { tag: 'SUBTOTAL', label: 'Subtotal', color: '#D97706' },
  { tag: 'DISCOUNT', label: 'Discount', color: '#EF4444' },
  { tag: 'TAX', label: 'Tax Amount', color: '#F59E0B' },
  { tag: 'DELIVERY', label: 'Delivery Fee', color: '#6366F1' },
  { tag: 'GRAND_TOTAL', label: 'Grand Total', color: '#DC2626' },
  { tag: 'PAID', label: 'Paid Amount', color: '#16A34A' },
  { tag: 'BALANCE', label: 'Balance Due', color: '#DC2626' },
  { tag: 'PAYMENT_METHOD', label: 'Payment Method', color: '#7C3AED' },
  { tag: 'ITEM_TABLE', label: 'Items Table Area', color: '#0891B2' },
  { tag: 'REMARKS', label: 'Remarks', color: '#64748B' },
]

interface FieldOverlay {
  id: string
  tag: string
  label: string
  color: string
  x: number
  y: number
  width: number
  height: number
  fontSize: number
}

export default function PDFCalibratorPage() {
  const { activeBrand } = useBrand()
  const queryClient = useQueryClient()
  const [uploadedTemplate, setUploadedTemplate] = useState<string | null>(null)
  const [fields, setFields] = useState<FieldOverlay[]>([])
  const [selectedField, setSelectedField] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 })
  const [isResizing, setIsResizing] = useState(false)
  const [activeTab, setActiveTab] = useState<'upload' | 'calibrate'>('upload')
  const canvasRef = useRef<HTMLDivElement>(null)

  const { data: brand } = useQuery({
    queryKey: ['brand', activeBrand.id],
    queryFn: () => brandsApi.get(activeBrand.id).then(r => r.data),
    enabled: activeBrand.id > 0,
  })

  const uploadMutation = useMutation({
    mutationFn: (file: File) => brandsApi.uploadTemplate(activeBrand.id, file),
    onSuccess: (res) => {
      toast.success(`Template uploaded! Detected ${res.data.fields_detected?.length || 0} fields`)
      queryClient.invalidateQueries({ queryKey: ['brand', activeBrand.id] })

      // Convert detected fields to overlays
      const detected = res.data.fields_detected || []
      const autoFields: FieldOverlay[] = detected.map((fieldName: string, i: number) => {
        const tag = FIELD_TAGS.find(t => t.tag === fieldName || t.label.toLowerCase().includes(fieldName.toLowerCase()))
        return {
          id: `field-${i}`,
          tag: fieldName,
          label: tag?.label || fieldName,
          color: tag?.color || '#6B7280',
          x: 50 + (i % 3) * 150,
          y: 50 + Math.floor(i / 3) * 40,
          width: 140,
          height: 28,
          fontSize: 11,
        }
      })
      if (autoFields.length > 0) setFields(autoFields)
      setActiveTab('calibrate')
    },
    onError: () => toast.error('Upload failed. Make sure backend is running.'),
  })

  const saveMutation = useMutation({
    mutationFn: () => {
      const mapping = {
        fields: fields.reduce((acc, f) => ({
          ...acc,
          [f.tag]: { x: f.x, y: f.y, width: f.width, height: f.height, fontSize: f.fontSize },
        }), {}),
        calibrated_at: new Date().toISOString(),
        calibrated_by: 'Visual Calibrator',
      }
      return brandsApi.updateTemplateMapping(activeBrand.id, mapping)
    },
    onSuccess: () => {
      toast.success('Calibration saved! PDF auto-fill will use these coordinates.')
      queryClient.invalidateQueries({ queryKey: ['brand', activeBrand.id] })
    },
  })

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      toast.error('Please upload a PDF file')
      return
    }
    // Preview
    const url = URL.createObjectURL(file)
    setUploadedTemplate(url)
    uploadMutation.mutate(file)
  }

  const addFieldFromTag = (tagDef: typeof FIELD_TAGS[0]) => {
    const existing = fields.find(f => f.tag === tagDef.tag)
    if (existing) {
      toast.error(`${tagDef.label} is already added`)
      return
    }
    setFields(prev => [...prev, {
      id: `field-${Date.now()}`,
      tag: tagDef.tag,
      label: tagDef.label,
      color: tagDef.color,
      x: 50,
      y: 50 + prev.length * 35,
      width: 140,
      height: 28,
      fontSize: 11,
    }])
  }

  const handleMouseDown = useCallback((e: React.MouseEvent, fieldId: string) => {
    e.preventDefault()
    e.stopPropagation()
    const rect = (e.target as HTMLElement).closest('[data-field]')?.getBoundingClientRect()
    const parentRect = canvasRef.current?.getBoundingClientRect()
    if (!rect || !parentRect) return

    setSelectedField(fieldId)
    setIsDragging(true)
    setDragOffset({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top,
    })
  }, [])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDragging || !selectedField || !canvasRef.current) return
    const parentRect = canvasRef.current.getBoundingClientRect()
    const newX = e.clientX - parentRect.left - dragOffset.x
    const newY = e.clientY - parentRect.top - dragOffset.y

    setFields(prev => prev.map(f =>
      f.id === selectedField ? { ...f, x: Math.max(0, newX), y: Math.max(0, newY) } : f
    ))
  }, [isDragging, selectedField, dragOffset])

  const handleMouseUp = useCallback(() => {
    setIsDragging(false)
  }, [])

  const updateField = (id: string, updates: Partial<FieldOverlay>) => {
    setFields(prev => prev.map(f => f.id === id ? { ...f, ...updates } : f))
  }

  const removeField = (id: string) => {
    setFields(prev => prev.filter(f => f.id !== id))
    if (selectedField === id) setSelectedField(null)
  }

  if (activeBrand.id === 0) {
    return (
      <div className="page-container flex items-center justify-center min-h-64">
        <div className="text-center">
          <Grid className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="font-semibold text-slate-600">Select a Brand Profile</h3>
          <p className="text-sm text-slate-400 mt-1">PDF calibration is per-brand</p>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="section-header">
        <div>
          <h1 className="section-title">🎯 PDF Template Calibrator</h1>
          <p className="text-sm text-slate-500">Upload your invoice PDF · drag fields to positions · save calibration</p>
        </div>
        {fields.length > 0 && (
          <button onClick={() => saveMutation.mutate()} className="btn-primary">
            <Save className="w-4 h-4" /> Save Calibration
          </button>
        )}
      </div>

      {/* Info Banner */}
      <div className="flex items-start gap-3 p-4 rounded-xl mb-5 border"
        style={{ background: 'var(--brand-surface)', borderColor: 'var(--brand-border)' }}>
        <Info className="w-4 h-4 flex-shrink-0 mt-0.5" style={{ color: 'var(--brand-primary)' }} />
        <div className="text-sm" style={{ color: 'var(--brand-text)' }}>
          <strong>How it works:</strong> Design your invoice in Adobe InDesign or Canva → Export as PDF →
          Upload here → Drag & drop field labels to their exact positions on the PDF → Save.
          The system will auto-fill these positions when generating invoices.
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 p-1 bg-slate-100 rounded-xl w-fit">
        {[
          { id: 'upload', label: '① Upload PDF' },
          { id: 'calibrate', label: '② Calibrate Fields' },
        ].map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id as any)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
              activeTab === tab.id ? 'bg-white shadow-sm text-slate-800' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'upload' && (
        <div className="card p-8 max-w-xl">
          <div className="flex flex-col items-center text-center">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mb-4"
              style={{ background: 'var(--brand-surface)' }}>
              <Upload className="w-8 h-8" style={{ color: 'var(--brand-primary)' }} />
            </div>
            <h3 className="font-bold text-slate-800 mb-2">Upload Invoice PDF Template</h3>
            <p className="text-sm text-slate-500 mb-6">
              Your designed invoice PDF — InDesign, Illustrator, Canva, Word — any source
            </p>

            {brand?.template_calibrated && (
              <div className="w-full p-3 rounded-xl bg-green-50 border border-green-200 text-sm text-green-700 mb-4 flex items-center gap-2">
                <Check className="w-4 h-4 flex-shrink-0" />
                Template already calibrated. Re-upload to replace.
              </div>
            )}

            <label className="btn-primary cursor-pointer">
              <Upload className="w-4 h-4" />
              Choose PDF File
              <input type="file" accept=".pdf" className="hidden" onChange={handleFileUpload} />
            </label>

            {uploadMutation.isPending && (
              <div className="mt-4 text-sm text-slate-500 flex items-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin" />
                Analyzing template layout with AI...
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'calibrate' && (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
          {/* Field Palette */}
          <div className="space-y-4">
            <div className="card p-4">
              <h3 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
                <Tag className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />
                Field Tags
              </h3>
              <p className="text-xs text-slate-400 mb-3">Click to add fields to the canvas</p>
              <div className="space-y-1.5">
                {FIELD_TAGS.map(tag => {
                  const isAdded = fields.some(f => f.tag === tag.tag)
                  return (
                    <button
                      key={tag.tag}
                      onClick={() => !isAdded && addFieldFromTag(tag)}
                      disabled={isAdded}
                      className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-xs transition-all ${
                        isAdded ? 'opacity-40 cursor-not-allowed' : 'hover:bg-slate-50 cursor-pointer'
                      }`}
                    >
                      <div className="w-3 h-3 rounded-full flex-shrink-0" style={{ background: tag.color }} />
                      <span className="font-medium text-slate-700">{tag.label}</span>
                      {isAdded && <span className="ml-auto text-green-500">✓</span>}
                    </button>
                  )
                })}
              </div>
            </div>

            {/* Selected Field Properties */}
            {selectedField && (
              <div className="card p-4">
                <h3 className="font-semibold text-slate-700 mb-3">Field Properties</h3>
                {(() => {
                  const field = fields.find(f => f.id === selectedField)
                  if (!field) return null
                  return (
                    <div className="space-y-3 text-xs">
                      <div>
                        <label className="text-slate-500 mb-1 block">X Position</label>
                        <input type="number" value={Math.round(field.x)}
                          onChange={e => updateField(field.id, { x: Number(e.target.value) })}
                          className="input-field text-xs" />
                      </div>
                      <div>
                        <label className="text-slate-500 mb-1 block">Y Position</label>
                        <input type="number" value={Math.round(field.y)}
                          onChange={e => updateField(field.id, { y: Number(e.target.value) })}
                          className="input-field text-xs" />
                      </div>
                      <div>
                        <label className="text-slate-500 mb-1 block">Width</label>
                        <input type="number" value={Math.round(field.width)}
                          onChange={e => updateField(field.id, { width: Number(e.target.value) })}
                          className="input-field text-xs" />
                      </div>
                      <div>
                        <label className="text-slate-500 mb-1 block">Font Size</label>
                        <input type="number" value={field.fontSize}
                          onChange={e => updateField(field.id, { fontSize: Number(e.target.value) })}
                          className="input-field text-xs" />
                      </div>
                      <button onClick={() => removeField(field.id)}
                        className="w-full flex items-center justify-center gap-2 p-2 rounded-xl bg-red-50 text-red-500 hover:bg-red-100 transition-colors text-xs font-semibold">
                        <Trash2 className="w-3.5 h-3.5" /> Remove Field
                      </button>
                    </div>
                  )
                })()}
              </div>
            )}
          </div>

          {/* Canvas Area */}
          <div className="lg:col-span-3">
            <div className="card overflow-hidden">
              <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between">
                <span className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                  <Crosshair className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />
                  PDF Canvas — Drag fields to their positions
                </span>
                <span className="text-xs text-slate-400">{fields.length} fields placed</span>
              </div>

              <div
                ref={canvasRef}
                className="relative overflow-hidden bg-slate-50"
                style={{ height: '600px' }}
                onMouseMove={handleMouseMove}
                onMouseUp={handleMouseUp}
                onMouseLeave={handleMouseUp}
                onClick={() => setSelectedField(null)}
              >
                {/* PDF preview / grid background */}
                {uploadedTemplate ? (
                  <iframe src={uploadedTemplate} className="w-full h-full border-0 pointer-events-none" />
                ) : (
                  <div className="absolute inset-0 flex items-center justify-center">
                    <div className="text-center">
                      <div className="w-48 h-64 border-2 border-dashed border-slate-300 rounded-xl flex flex-col items-center justify-center mx-auto mb-4 text-slate-300">
                        <FileTextIcon className="w-12 h-12 mb-2" />
                        <span className="text-sm">PDF Preview Area</span>
                      </div>
                      <p className="text-xs text-slate-400">Upload a PDF template to see it here</p>
                      <p className="text-xs text-slate-400 mt-1">Fields placed below will overlay the PDF</p>
                    </div>
                  </div>
                )}

                {/* Grid overlay */}
                <div className="absolute inset-0 pointer-events-none opacity-[0.03]"
                  style={{
                    backgroundImage: 'linear-gradient(#000 1px, transparent 1px), linear-gradient(90deg, #000 1px, transparent 1px)',
                    backgroundSize: '20px 20px',
                  }} />

                {/* Field Overlays */}
                {fields.map(field => (
                  <div
                    key={field.id}
                    data-field={field.id}
                    className={`pdf-field-overlay select-none ${isDragging && selectedField === field.id ? 'opacity-80' : ''}`}
                    style={{
                      left: field.x,
                      top: field.y,
                      width: field.width,
                      height: field.height,
                      borderColor: field.color,
                      color: field.color,
                      boxShadow: selectedField === field.id ? `0 0 0 2px ${field.color}` : 'none',
                      zIndex: selectedField === field.id ? 50 : 10,
                    }}
                    onMouseDown={e => handleMouseDown(e, field.id)}
                    onClick={e => { e.stopPropagation(); setSelectedField(field.id) }}
                  >
                    <Move className="w-2.5 h-2.5 mr-1 flex-shrink-0" />
                    <span className="truncate" style={{ fontSize: 10 }}>{field.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {fields.length > 0 && (
              <div className="mt-4 flex justify-end">
                <button onClick={() => saveMutation.mutate()} className="btn-primary">
                  <Save className="w-4 h-4" />
                  {saveMutation.isPending ? 'Saving...' : 'Save Calibration'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// Avoid import conflict
function FileTextIcon({ className }: { className: string }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
  </svg>
}

// Need to import Check for template calibrated check
function Check({ className }: { className: string }) {
  return <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
  </svg>
}
