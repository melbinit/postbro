"use client"

import type React from "react"

import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { toast } from "sonner"
import { useState, useEffect } from "react"
import { profileApi, type User } from "@/lib/api"
import { Skeleton } from "@/components/ui/skeleton"
import { User as UserIcon, Mail, Building2, Save, Loader2 } from "lucide-react"

export function ProfileForm() {
  const [isLoading, setIsLoading] = useState(false)
  const [isFetching, setIsFetching] = useState(true)
  const [user, setUser] = useState<User | null>(null)
  const [formData, setFormData] = useState({
    full_name: '',
    company_name: '',
  })

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setIsFetching(true)
        const data = await profileApi.getProfile()
        setUser(data)
        setFormData({
          full_name: data.full_name || '',
          company_name: data.company_name || '',
        })
      } catch (error) {
        toast.error('Failed to load profile')
        console.error('Failed to fetch profile:', error)
      } finally {
        setIsFetching(false)
      }
    }

    fetchProfile()
  }, [])

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setIsLoading(true)

    try {
      const updated = await profileApi.updateProfile({
        full_name: formData.full_name || undefined,
        company_name: formData.company_name || undefined,
      })
      setUser(updated)
      toast.success("Profile updated successfully")
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Failed to update profile")
    } finally {
      setIsLoading(false)
    }
  }

  if (isFetching) {
    return (
      <div className="bg-card rounded-2xl border border-border/50 overflow-hidden">
        <div className="p-6 border-b border-border/50 bg-gradient-to-r from-primary/5 via-transparent to-transparent">
          <Skeleton className="h-6 w-48 mb-2" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="p-6 space-y-6">
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-12 w-full rounded-xl" />
        </div>
      </div>
    )
  }

  // Get initials for avatar
  const initials = user?.full_name
    ?.split(' ')
    .map((n) => n[0])
    .join('')
    .toUpperCase() || user?.email[0].toUpperCase() || 'U'

  return (
    <div className="bg-card rounded-2xl border border-border/50 overflow-hidden">
      {/* Header with avatar */}
      <div className="p-6 border-b border-border/50 bg-gradient-to-r from-primary/5 via-transparent to-transparent">
        <div className="flex items-center gap-4">
          <div className="relative">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/10 flex items-center justify-center text-xl font-bold text-primary ring-4 ring-background">
              {initials}
            </div>
            <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-green-500 border-2 border-background" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">{user?.full_name || 'Your Profile'}</h2>
            <p className="text-sm text-muted-foreground">{user?.email}</p>
          </div>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="p-6 space-y-6">
        {/* Full Name Field */}
        <div className="space-y-2.5">
          <Label htmlFor="full_name" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            <UserIcon className="size-3.5" />
            Full Name
          </Label>
          <Input
            id="full_name"
            value={formData.full_name}
            onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
            placeholder="John Doe"
            className="h-11 rounded-xl bg-background border-border/60 focus:border-primary/50"
          />
        </div>

        {/* Email Field - Read Only */}
        <div className="space-y-2.5">
          <Label htmlFor="email" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            <Mail className="size-3.5" />
            Email Address
          </Label>
          <div className="relative">
            <Input
              id="email"
              type="email"
              value={user?.email || ''}
              disabled
              className="h-11 rounded-xl bg-muted/50 border-border/40 text-muted-foreground pr-24"
            />
            <span className="absolute right-3 top-1/2 -translate-y-1/2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/60 bg-muted px-2 py-1 rounded">
              Read only
            </span>
          </div>
          <p className="text-xs text-muted-foreground">Email is managed by your authentication provider</p>
        </div>

        {/* Company Field */}
        <div className="space-y-2.5">
          <Label htmlFor="company_name" className="text-xs font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            <Building2 className="size-3.5" />
            Company
          </Label>
          <Input
            id="company_name"
            value={formData.company_name}
            onChange={(e) => setFormData({ ...formData, company_name: e.target.value })}
            placeholder="Your Company"
            className="h-11 rounded-xl bg-background border-border/60 focus:border-primary/50"
          />
        </div>

        {/* Submit Button */}
        <div className="flex justify-end pt-4 border-t border-border/30">
          <Button 
            type="submit" 
            disabled={isLoading}
            className="h-10 px-5 rounded-xl shadow-md shadow-primary/20 hover:shadow-lg hover:shadow-primary/25 transition-all"
          >
            {isLoading ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin mr-2" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
