'use client'

import { useState } from 'react'
import AppRuntime from '@/components/AppRuntime'
import PhoneFrame from '@/components/PhoneFrame'
import PlatformToggle from '@/components/PlatformToggle'
import type { Module } from '@/types'

interface AppPreviewProps {
  appId: string
  appName: string
  modules: Module[]
  activeModules: string[]
  primaryColor: string
  secondaryColor: string
  logoUrl: string
  homeModule: string
  homeImageUrl?: string
  editable?: boolean
  onModulesChange?: (names: string[]) => void
  onConfigureModule?: (name: string) => void
  configVersion?: number
}

export default function AppPreview(props: AppPreviewProps) {
  const [platform, setPlatform] = useState<'android' | 'ios'>('android')

  return (
    <div>
      <p className="text-sm font-medium text-gray-700 mb-1">Preview do aplicativo</p>
      {props.editable && (
        <p className="text-xs text-gray-400 mb-2">
          Toque no ☰ pra reordenar ou configurar os módulos
        </p>
      )}
      <PlatformToggle value={platform} onChange={setPlatform} />
      <PhoneFrame platform={platform}>
        <AppRuntime mode="owner" {...props} />
      </PhoneFrame>
    </div>
  )
}
