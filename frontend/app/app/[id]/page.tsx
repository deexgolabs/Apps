import type { Metadata } from 'next'
import AppPublicClient from './AppPublicClient'

interface PageProps {
  params: Promise<{ id: string }>
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { id } = await params
  return {
    manifest: `/manifest/${id}`,
  }
}

export default async function PublicAppPage({ params }: PageProps) {
  const { id } = await params
  return <AppPublicClient appId={id} />
}
