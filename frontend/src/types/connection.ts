export type Connection = {
  id: number
  name: string
  role: string
  summary: string
  matchScore: number
  location: string
  sharedInterests: string[]
  avatar: string
  detectedPhoto: string
  professionalSummary: string
  experience: string[]
  education: string
  skills: string[]
  linkedin?: string
  twitter?: string
  instagram?: string
  conversationStarters: string[]
}
