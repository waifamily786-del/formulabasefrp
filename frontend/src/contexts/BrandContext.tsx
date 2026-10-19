import React, { createContext, useContext, useState, useCallback, ReactNode, useEffect } from 'react'

export interface Brand {
  id: number
  name: string
  full_name: string | null
  tagline: string | null
  invoice_prefix: string
  phone: string | null
  address: string | null
  email: string | null
  theme_primary_color: string
  theme_gradient_start: string
  theme_gradient_mid: string
  theme_gradient_end: string
  theme_surface_tint: string
  theme_border_tint: string
  theme_deep_text: string
  commercial_tax_rate: number
  template_calibrated: boolean
  invoice_sequence: number
  is_active: boolean
}

// Master ERP "brand" sentinel
export const MASTER_BRAND: Brand = {
  id: 0,
  name: 'MASTER',
  full_name: 'Formula Base Master ERP',
  tagline: 'Unified OEM Control Center',
  invoice_prefix: 'ERP-',
  phone: null,
  address: null,
  email: null,
  theme_primary_color: '#1D4ED8',
  theme_gradient_start: '#1E3A8A',
  theme_gradient_mid: '#1D4ED8',
  theme_gradient_end: '#3B82F6',
  theme_surface_tint: '#EFF6FF',
  theme_border_tint: '#BFDBFE',
  theme_deep_text: '#1E3A8A',
  commercial_tax_rate: 0,
  template_calibrated: false,
  invoice_sequence: 0,
  is_active: true,
}

interface BrandContextType {
  activeBrand: Brand
  brands: Brand[]
  setBrands: (b: Brand[]) => void
  switchBrand: (brand: Brand) => void
}

const BrandContext = createContext<BrandContextType | null>(null)

export function BrandProvider({ children }: { children: ReactNode }) {
  const [activeBrand, setActiveBrand] = useState<Brand>(MASTER_BRAND)
  const [brands, setBrands] = useState<Brand[]>([])

  const applyTheme = useCallback((brand: Brand) => {
    const root = document.documentElement
    root.setAttribute('data-brand', brand.name)
    root.style.setProperty('--brand-primary', brand.theme_primary_color)
    root.style.setProperty('--brand-gradient-from', brand.theme_gradient_start)
    root.style.setProperty('--brand-gradient-mid', brand.theme_gradient_mid)
    root.style.setProperty('--brand-gradient-to', brand.theme_gradient_end)
    root.style.setProperty('--brand-surface', brand.theme_surface_tint)
    root.style.setProperty('--brand-border', brand.theme_border_tint)
    root.style.setProperty('--brand-text', brand.theme_deep_text)
    root.style.setProperty('--brand-shadow', `${brand.theme_primary_color}33`)
  }, [])

  const switchBrand = useCallback((brand: Brand) => {
    setActiveBrand(brand)
    applyTheme(brand)
    localStorage.setItem('active_brand_id', String(brand.id))
  }, [applyTheme])

  // Apply Master ERP theme on mount
  useEffect(() => {
    applyTheme(MASTER_BRAND)
  }, [applyTheme])

  return (
    <BrandContext.Provider value={{ activeBrand, brands, setBrands, switchBrand }}>
      {children}
    </BrandContext.Provider>
  )
}

export function useBrand() {
  const ctx = useContext(BrandContext)
  if (!ctx) throw new Error('useBrand must be inside BrandProvider')
  return ctx
}
