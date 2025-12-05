"use client"

import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { useEffect, useState } from "react"
import { profileApi, type User } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"

export function ProfileHeader() {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        const data = await profileApi.getProfile()
        setUser(data)
      } catch (error) {
        console.error('Failed to fetch profile:', error)
      } finally {
        setIsLoading(false)
      }
    }

    fetchProfile()
  }, [])

  if (isLoading) {
    return (
      <div className="flex flex-col md:flex-row items-start md:items-center gap-6 mb-8">
        <div className="flex items-center gap-4">
          <Skeleton className="size-20 rounded-full" />
          <div className="space-y-2">
            <Skeleton className="h-7 w-48" />
            <Skeleton className="h-5 w-64" />
          </div>
        </div>
      </div>
    )
  }

  if (!user) {
    return null
  }

  const initials = user.full_name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase() || user.email[0].toUpperCase()

  return (
    <div className="flex flex-col md:flex-row items-start md:items-center gap-6 mb-8">
      <div className="flex items-center gap-4">
        <Avatar className="size-20 border-2 border-border">
          <AvatarImage src={user.profile_image || undefined} alt={user.full_name || user.email} />
          <AvatarFallback className="text-xl bg-primary/10 text-primary font-medium">
            {initials}
          </AvatarFallback>
        </Avatar>
        <div>
          <h1 className="text-2xl font-bold">{user.full_name || 'User'}</h1>
          <div className="flex items-center gap-2 text-muted-foreground">
            <span>{user.email}</span>
            {user.email_verified && (
              <Badge variant="outline" className="text-green-600 bg-green-500/10 border-green-500/20">
                Verified
              </Badge>
            )}
          </div>
          {user.company_name && (
            <p className="text-sm text-muted-foreground mt-1">{user.company_name}</p>
          )}
        </div>
      </div>
    </div>
  )
}
