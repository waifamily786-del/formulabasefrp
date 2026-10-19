import React, { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useForm, useFieldArray } from 'react-hook-form'
import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Plus, Trash2, User, Phone, MapPin, Package, Percent,
  Truck, CreditCard, Printer, Send, Search, ChevronDown,
  X, Check, FileText, Loader2, RefreshCw
} from 'lucide-react'
import { posApi } from '../lib/api'
import { useBrand } from '../contexts/BrandContext'
import { format } from 'date-fns'

interface InvoiceItem {
  product_id: number
  product_name: string
  unit: string
  qty: number
  foc_qty: number
  price_tier: string
  custom_unit_price: number | null
  unit_price: number
  item_discount_percent: number
  line_total: number
  available_stock: number
  prices: Record<string, number>
}

interface InvoiceFormData {
  customer_id: number | null
  customer_name: string
  customer_phone: string
  customer_address: string
  discount_percent: number
  discount_amount: number
  delivery_fee: number
  payment_method: string
  paid_amount: number | null
  remarks: string
  generate_pdf: boolean
}

const PRICE_TIERS = [
  { value: 'RETAIL', label: 'Retail' },
  { value: 'WHOLESALE', label: 'Wholesale' },
  { value: 'DISTRIBUTOR', label: 'Distributor' },
  { value: 'VIP', label: 'VIP' },
]

const PAYMENT_METHODS = [
  { value: 'CASH', label: '💵 Cash', icon: '💵' },
  { value: 'KPAY', label: '📱 KPay', icon: '📱' },
  { value: 'WAVEPAY', label: '🌊 WavePay', icon: '🌊' },
  { value: 'BANK', label: '🏦 Bank Transfer', icon: '🏦' },
  { value: 'CREDIT', label: '📋 Credit (အကြွေး)', icon: '📋' },
]

export default function InvoicePage() {
  const { activeBrand } = useBrand()
  const [items, setItems] = useState<InvoiceItem[]>([])
  const [selectedCustomer, setSelectedCustomer] = useState<any>(null)
  const [customerSearch, setCustomerSearch] = useState('')
  const [productSearch, setProductSearch] = useState('')
  const [showCustomerDropdown, setShowCustomerDropdown] = useState(false)
  const [showProductDropdown, setShowProductDropdown] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [invoiceResult, setInvoiceResult] = useState<any>(null)

  const { register, handleSubmit, watch, setValue, formState: { errors } } = useForm<InvoiceFormData>({
    defaultValues: {
      discount_percent: 0,
      discount_amount: 0,
      delivery_fee: 0,
      payment_method: 'CASH',
      generate_pdf: true,
    }
  })

  const watchPayment = watch('payment_method')
  const watchPaidAmount = watch('paid_amount')
  const watchDiscount = watch('discount_percent')
  const watchDiscountAmt = watch('discount_amount')
  const watchDelivery = watch('delivery_fee')

  const { data: customers = [] } = useQuery({
    queryKey: ['customers', activeBrand.id],
    queryFn: () => posApi.customers(activeBrand.id).then(r => r.data),
    enabled: activeBrand.id > 0,
  })

  const { data: products = [] } = useQuery({
    queryKey: ['products', activeBrand.id],
    queryFn: () => posApi.products(activeBrand.id).then(r => r.data),
    enabled: activeBrand.id > 0,
  })

  const filteredCustomers = customers.filter((c: any) =>
    c.name.toLowerCase().includes(customerSearch.toLowerCase()) ||
    (c.phone && c.phone.includes(customerSearch))
  )

  const filteredProducts = products.filter((p: any) =>
    p.name.toLowerCase().includes(productSearch.toLowerCase()) ||
    (p.sku && p.sku.toLowerCase().includes(productSearch.toLowerCase()))
  )

  // Calculations
  const subtotal = items.reduce((s, i) => s + i.line_total, 0)
  const discountAmt = watchDiscount > 0
    ? subtotal * (watchDiscount / 100)
    : (watchDiscountAmt || 0)
  const taxable = subtotal - discountAmt
  const taxAmount = taxable * (activeBrand.commercial_tax_rate / 100)
  const grandTotal = taxable + taxAmount + (watchDelivery || 0)
  const paidAmount = watchPaidAmount !== null && watchPaidAmount !== undefined ? Number(watchPaidAmount) : grandTotal
  const changeAmount = Math.max(0, paidAmount - grandTotal)
  const creditAmount = Math.max(0, grandTotal - paidAmount)

  const addProduct = (product: any) => {
    const defaultPriceTier = selectedCustomer?.price_tier || 'RETAIL'
    const unitPrice = product.prices[defaultPriceTier] || product.prices.RETAIL || 0
    const newItem: InvoiceItem = {
      product_id: product.id,
      product_name: product.name,
      unit: product.unit,
      qty: 1,
      foc_qty: 0,
      price_tier: defaultPriceTier,
      custom_unit_price: null,
      unit_price: unitPrice,
      item_discount_percent: 0,
      line_total: unitPrice,
      available_stock: product.current_stock,
      prices: product.prices,
    }
    setItems(prev => [...prev, newItem])
    setProductSearch('')
    setShowProductDropdown(false)
  }

  const updateItem = (idx: number, field: keyof InvoiceItem, value: any) => {
    setItems(prev => {
      const updated = [...prev]
      const item = { ...updated[idx] }
      ;(item as any)[field] = value

      if (field === 'price_tier') {
        item.unit_price = item.prices[value] || item.prices.RETAIL || 0
      }
      if (field === 'custom_unit_price' && value !== null) {
        item.unit_price = Number(value)
      }

      const effectivePrice = item.custom_unit_price !== null ? Number(item.custom_unit_price) : item.unit_price
      const discAmt = effectivePrice * item.qty * (item.item_discount_percent / 100)
      item.line_total = effectivePrice * item.qty - discAmt
      updated[idx] = item
      return updated
    })
  }

  const removeItem = (idx: number) => {
    setItems(prev => prev.filter((_, i) => i !== idx))
  }

  const selectCustomer = (cust: any) => {
    setSelectedCustomer(cust)
    setValue('customer_id', cust.id)
    setValue('customer_name', cust.name)
    setValue('customer_phone', cust.phone || '')
    setValue('customer_address', cust.address || '')
    setCustomerSearch(cust.name)
    setShowCustomerDropdown(false)
  }

  const onSubmit = async (formData: InvoiceFormData) => {
    if (items.length === 0) {
      toast.error('Add at least one product')
      return
    }
    setIsSubmitting(true)
    try {
      const payload = {
        brand_id: activeBrand.id,
        customer_id: formData.customer_id || undefined,
        customer_name: !formData.customer_id ? (formData.customer_name || 'Walk-in Customer') : undefined,
        customer_phone: !formData.customer_id ? formData.customer_phone : undefined,
        customer_address: !formData.customer_id ? formData.customer_address : undefined,
        items: items.map(item => ({
          product_id: item.product_id,
          qty: item.qty,
          foc_qty: item.foc_qty,
          price_tier: item.price_tier,
          custom_unit_price: item.custom_unit_price,
          item_discount_percent: item.item_discount_percent,
        })),
        discount_percent: formData.discount_percent || 0,
        discount_amount: formData.discount_percent > 0 ? 0 : (formData.discount_amount || 0),
        delivery_fee: formData.delivery_fee || 0,
        payment_method: formData.payment_method,
        paid_amount: watchPayment === 'CREDIT' ? 0 : (formData.paid_amount || grandTotal),
        remarks: formData.remarks,
        generate_pdf: formData.generate_pdf,
      }
      const res = await posApi.createInvoice(payload)
      setInvoiceResult(res.data)
      toast.success(`Invoice ${res.data.invoice_number} created!`)
    } catch (err: any) {
      toast.error(err.response?.data?.detail || 'Failed to create invoice')
    } finally {
      setIsSubmitting(false)
    }
  }

  const resetForm = () => {
    setItems([])
    setSelectedCustomer(null)
    setCustomerSearch('')
    setInvoiceResult(null)
    setValue('customer_id', null)
    setValue('customer_name', '')
    setValue('customer_phone', '')
    setValue('customer_address', '')
    setValue('discount_percent', 0)
    setValue('discount_amount', 0)
    setValue('delivery_fee', 0)
    setValue('paid_amount', null as any)
    setValue('remarks', '')
  }

  if (activeBrand.id === 0) {
    return (
      <div className="page-container flex items-center justify-center min-h-64">
        <div className="text-center">
          <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
          <h3 className="font-semibold text-slate-600 mb-1">Select a Brand Profile</h3>
          <p className="text-sm text-slate-400">Switch to a brand profile from the sidebar to create invoices</p>
        </div>
      </div>
    )
  }

  if (invoiceResult) {
    return (
      <div className="page-container">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          className="max-w-lg mx-auto"
        >
          <div className="card p-8 text-center">
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4"
              style={{ background: 'var(--brand-surface)' }}>
              <Check className="w-8 h-8" style={{ color: 'var(--brand-primary)' }} />
            </div>
            <h2 className="text-xl font-bold text-slate-800 mb-1">Invoice Created!</h2>
            <p className="text-slate-500 mb-6">{invoiceResult.invoice_number}</p>

            <div className="space-y-2 text-sm mb-6 p-4 rounded-xl" style={{ background: 'var(--brand-surface)' }}>
              {[
                ['Subtotal', `MMK ${invoiceResult.subtotal?.toLocaleString()}`],
                ['Discount', `- MMK ${invoiceResult.discount_amount?.toLocaleString()}`],
                ['Tax', `MMK ${invoiceResult.tax_amount?.toLocaleString()}`],
                ['Delivery', `MMK ${invoiceResult.delivery_fee?.toLocaleString()}`],
                ['Grand Total', `MMK ${invoiceResult.grand_total?.toLocaleString()}`],
                ['Paid', `MMK ${invoiceResult.paid_amount?.toLocaleString()}`],
                ...(invoiceResult.change_amount > 0 ? [['Change', `MMK ${invoiceResult.change_amount?.toLocaleString()}`]] : []),
                ...(invoiceResult.credit_amount > 0 ? [['Credit (Due)', `MMK ${invoiceResult.credit_amount?.toLocaleString()}`]] : []),
              ].map(([k, v]) => (
                <div key={k} className="flex justify-between">
                  <span className="text-slate-500">{k}</span>
                  <span className="font-semibold text-slate-800">{v}</span>
                </div>
              ))}
            </div>

            {invoiceResult.pdf_warning && (
              <div className="text-xs text-amber-600 bg-amber-50 p-3 rounded-xl mb-4">
                ⚠️ {invoiceResult.pdf_warning}
              </div>
            )}
            {invoiceResult.pdf_path && (
              <div className="text-xs text-green-600 bg-green-50 p-3 rounded-xl mb-4">
                ✅ PDF generated successfully
              </div>
            )}

            <div className="flex gap-3">
              <button onClick={resetForm} className="btn-secondary flex-1">
                <Plus className="w-4 h-4" /> New Invoice
              </button>
              <button onClick={() => window.print()} className="btn-primary flex-1">
                <Printer className="w-4 h-4" /> Print
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="section-header">
        <div>
          <h1 className="section-title">⚡ Quick Invoice Builder</h1>
          <p className="text-sm text-slate-500">{activeBrand.full_name || activeBrand.name}</p>
        </div>
        <div className="text-right text-xs text-slate-400">
          <div className="font-semibold text-slate-600">{format(new Date(), 'dd MMM yyyy')}</div>
          <div>{activeBrand.invoice_prefix}{String(activeBrand.invoice_sequence).padStart(5, '0')}</div>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Left: Customer + Products */}
          <div className="lg:col-span-2 space-y-4">
            {/* Customer Section */}
            <div className="card p-5">
              <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
                <User className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />
                Customer
              </h3>
              <div className="relative mb-3">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  value={customerSearch}
                  onChange={e => { setCustomerSearch(e.target.value); setShowCustomerDropdown(true) }}
                  onFocus={() => setShowCustomerDropdown(true)}
                  placeholder="Search existing customer..."
                  className="input-field pl-10"
                />
                {showCustomerDropdown && filteredCustomers.length > 0 && (
                  <div className="absolute z-20 w-full mt-1 bg-white rounded-xl border border-slate-100 shadow-card-hover max-h-48 overflow-y-auto">
                    {filteredCustomers.map((cust: any) => (
                      <button
                        key={cust.id}
                        type="button"
                        onClick={() => selectCustomer(cust)}
                        className="w-full px-4 py-2.5 text-left hover:bg-slate-50 flex items-center justify-between"
                      >
                        <div>
                          <div className="text-sm font-medium text-slate-800">{cust.name}</div>
                          <div className="text-xs text-slate-400">{cust.phone}</div>
                        </div>
                        {cust.outstanding_credit > 0 && (
                          <span className="text-xs text-red-500">CR: {cust.outstanding_credit.toLocaleString()}</span>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="grid grid-cols-3 gap-3">
                <div>
                  <input {...register('customer_name')} placeholder="Customer name" className="input-field" />
                </div>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
                  <input {...register('customer_phone')} placeholder="Phone" className="input-field pl-9" />
                </div>
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
                  <input {...register('customer_address')} placeholder="Address" className="input-field pl-9" />
                </div>
              </div>
            </div>

            {/* Products Section */}
            <div className="card p-5">
              <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
                <Package className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />
                Products
              </h3>

              {/* Product Search */}
              <div className="relative mb-4">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                <input
                  value={productSearch}
                  onChange={e => { setProductSearch(e.target.value); setShowProductDropdown(true) }}
                  onFocus={() => setShowProductDropdown(true)}
                  placeholder="Search product to add..."
                  className="input-field pl-10"
                />
                {showProductDropdown && productSearch && filteredProducts.length > 0 && (
                  <div className="absolute z-20 w-full mt-1 bg-white rounded-xl border border-slate-100 shadow-card-hover max-h-56 overflow-y-auto">
                    {filteredProducts.map((p: any) => (
                      <button
                        key={p.id}
                        type="button"
                        onClick={() => addProduct(p)}
                        className="w-full px-4 py-2.5 text-left hover:bg-slate-50 flex items-center justify-between"
                      >
                        <div>
                          <div className="text-sm font-medium text-slate-800">{p.name}</div>
                          <div className="text-xs text-slate-400">{p.sku} · Stock: {p.current_stock} {p.unit}</div>
                        </div>
                        <span className="text-xs font-semibold" style={{ color: 'var(--brand-primary)' }}>
                          MMK {(p.prices?.RETAIL || 0).toLocaleString()}
                        </span>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Items Table */}
              {items.length > 0 ? (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Product</th>
                        <th>Tier</th>
                        <th>Qty</th>
                        <th>FOC</th>
                        <th>Unit Price</th>
                        <th>Disc%</th>
                        <th>Total</th>
                        <th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item, idx) => (
                        <tr key={idx}>
                          <td>
                            <div className="font-medium text-slate-800 text-xs">{item.product_name}</div>
                            <div className="text-xs text-slate-400">Stock: {item.available_stock}</div>
                          </td>
                          <td>
                            <select
                              value={item.price_tier}
                              onChange={e => updateItem(idx, 'price_tier', e.target.value)}
                              className="text-xs border border-slate-200 rounded-lg px-2 py-1 outline-none"
                            >
                              {PRICE_TIERS.map(t => (
                                <option key={t.value} value={t.value}>{t.label}</option>
                              ))}
                            </select>
                          </td>
                          <td>
                            <input
                              type="number"
                              value={item.qty}
                              min={0.01}
                              step={0.01}
                              onChange={e => updateItem(idx, 'qty', parseFloat(e.target.value) || 1)}
                              className="w-16 text-xs border border-slate-200 rounded-lg px-2 py-1 outline-none text-center"
                            />
                          </td>
                          <td>
                            <input
                              type="number"
                              value={item.foc_qty}
                              min={0}
                              onChange={e => updateItem(idx, 'foc_qty', parseFloat(e.target.value) || 0)}
                              className="w-12 text-xs border border-slate-200 rounded-lg px-2 py-1 outline-none text-center"
                            />
                          </td>
                          <td>
                            <input
                              type="number"
                              value={item.custom_unit_price !== null ? item.custom_unit_price : item.unit_price}
                              onChange={e => updateItem(idx, 'custom_unit_price', parseFloat(e.target.value))}
                              className="w-24 text-xs border border-slate-200 rounded-lg px-2 py-1 outline-none text-right"
                            />
                          </td>
                          <td>
                            <input
                              type="number"
                              value={item.item_discount_percent}
                              min={0}
                              max={100}
                              onChange={e => updateItem(idx, 'item_discount_percent', parseFloat(e.target.value) || 0)}
                              className="w-12 text-xs border border-slate-200 rounded-lg px-2 py-1 outline-none text-center"
                            />
                          </td>
                          <td className="font-semibold text-sm">{item.line_total.toLocaleString()}</td>
                          <td>
                            <button type="button" onClick={() => removeItem(idx)}
                              className="p-1 rounded-lg hover:bg-red-50 hover:text-red-500 text-slate-400 transition-colors">
                              <X className="w-3.5 h-3.5" />
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="border-2 border-dashed border-slate-200 rounded-xl py-8 text-center text-sm text-slate-400">
                  Search and add products above
                </div>
              )}
            </div>
          </div>

          {/* Right: Summary & Payment */}
          <div className="space-y-4">
            {/* Discounts */}
            <div className="card p-5">
              <h3 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
                <Percent className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />
                Discounts & Fees
              </h3>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">Discount %</label>
                  <input type="number" {...register('discount_percent', { min: 0, max: 100 })}
                    className="input-field" placeholder="0" />
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">Or Fixed Amount (MMK)</label>
                  <input type="number" {...register('discount_amount', { min: 0 })}
                    className="input-field" placeholder="0" />
                </div>
                <div>
                  <label className="text-xs text-slate-500 mb-1 block flex items-center gap-1">
                    <Truck className="w-3 h-3" /> Delivery Fee (MMK)
                  </label>
                  <input type="number" {...register('delivery_fee', { min: 0 })}
                    className="input-field" placeholder="0" />
                </div>
              </div>
            </div>

            {/* Payment Method */}
            <div className="card p-5">
              <h3 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
                <CreditCard className="w-4 h-4" style={{ color: 'var(--brand-primary)' }} />
                Payment
              </h3>
              <div className="grid grid-cols-2 gap-2 mb-3">
                {PAYMENT_METHODS.map(pm => (
                  <button
                    key={pm.value}
                    type="button"
                    onClick={() => setValue('payment_method', pm.value)}
                    className={`p-2.5 rounded-xl text-xs font-semibold border transition-all ${
                      watchPayment === pm.value
                        ? 'text-white border-transparent'
                        : 'border-slate-200 text-slate-600 hover:border-[var(--brand-border)]'
                    }`}
                    style={watchPayment === pm.value ? {
                      background: 'var(--brand-primary)',
                    } : {}}
                  >
                    {pm.label}
                  </button>
                ))}
              </div>

              {watchPayment !== 'CREDIT' && (
                <div>
                  <label className="text-xs text-slate-500 mb-1 block">Cash Received (MMK)</label>
                  <input type="number" {...register('paid_amount')}
                    placeholder={grandTotal.toLocaleString()}
                    className="input-field font-mono" />
                </div>
              )}
            </div>

            {/* Totals Summary */}
            <div className="card p-5">
              <div className="space-y-2 text-sm mb-4">
                {[
                  ['Subtotal', subtotal.toLocaleString()],
                  discountAmt > 0 ? ['Discount', `-${discountAmt.toLocaleString()}`] : null,
                  activeBrand.commercial_tax_rate > 0 ? [`CT (${activeBrand.commercial_tax_rate}%)`, taxAmount.toLocaleString()] : null,
                  (watchDelivery || 0) > 0 ? ['Delivery', (watchDelivery || 0).toLocaleString()] : null,
                ].filter(Boolean).map(([k, v]) => (
                  <div key={k} className="flex justify-between text-slate-600">
                    <span>{k}</span>
                    <span className="font-mono">{v}</span>
                  </div>
                ))}
                <div className="border-t border-slate-100 pt-2 flex justify-between">
                  <span className="font-bold text-slate-800">Grand Total</span>
                  <span className="font-bold text-lg font-mono" style={{ color: 'var(--brand-primary)' }}>
                    {grandTotal.toLocaleString()}
                  </span>
                </div>
                {changeAmount > 0 && (
                  <div className="flex justify-between text-green-600 text-xs">
                    <span>Change</span>
                    <span className="font-mono">{changeAmount.toLocaleString()}</span>
                  </div>
                )}
                {creditAmount > 0 && (
                  <div className="flex justify-between text-red-500 text-xs">
                    <span>Credit Due</span>
                    <span className="font-mono">{creditAmount.toLocaleString()}</span>
                  </div>
                )}
              </div>

              <div>
                <label className="text-xs text-slate-500 mb-1 block">Remarks</label>
                <textarea {...register('remarks')} rows={2}
                  className="input-field resize-none" placeholder="Notes..." />
              </div>

              <div className="flex items-center gap-2 my-3">
                <input type="checkbox" {...register('generate_pdf')} id="gen-pdf"
                  className="rounded" />
                <label htmlFor="gen-pdf" className="text-xs text-slate-600">Generate PDF Invoice</label>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || items.length === 0}
                className="btn-primary w-full justify-center py-3"
              >
                {isSubmitting ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Processing...</>
                ) : (
                  <><Check className="w-4 h-4" /> Generate Invoice</>
                )}
              </button>
            </div>
          </div>
        </div>
      </form>
    </div>
  )
}
