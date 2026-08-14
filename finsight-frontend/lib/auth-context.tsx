'use client'

import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { onAuthStateChanged, User } from 'firebase/auth'
import {
  auth,
  signInWithGoogle as firebaseGoogleSignIn,
  signOutUser as firebaseSignOut,
} from './firebase'

interface AuthContextType {
  user: User | null
  token: string | null
  loading: boolean
  signInWithGoogle: () => Promise<User>
  logout: () => Promise<void>
}

const AuthContext = React.createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async currentUser => {
      setUser(currentUser)
      if (currentUser) {
        try {
          const idToken = await currentUser.getIdToken()
          setToken(idToken)
        } catch (err) {
          console.error('Failed to retrieve Firebase ID token:', err)
          setToken(null)
        }
      } else {
        setToken(null)
      }
      setLoading(false)
    })

    return () => unsubscribe()
  }, [])

  const signInWithGoogle = async (): Promise<User> => {
    setLoading(true)
    try {
      const loggedUser = await firebaseGoogleSignIn()
      setUser(loggedUser)
      const idToken = await loggedUser.getIdToken()
      setToken(idToken)
      return loggedUser
    } catch (err: unknown) {
      const firebaseError = err as { code?: string; message?: string }
      console.error('Google Sign-In error:', firebaseError)
      if (firebaseError?.code === 'auth/unauthorized-domain') {
        alert('Firebase Auth Error: Domain is not authorized. Please add "localhost" and "127.0.0.1" under Firebase Console -> Authentication -> Settings -> Authorized domains.')
      } else if (firebaseError?.code === 'auth/popup-blocked') {
        alert('Popup was blocked by your browser. Please allow popups for this site to sign in with Google.')
      } else if (firebaseError?.code !== 'auth/popup-closed-by-user') {
        alert(`Google Sign-In failed: ${firebaseError?.message || 'Unknown error'}`)
      }
      throw err
    } finally {
      setLoading(false)
    }
  }

  const logout = async (): Promise<void> => {
    await firebaseSignOut()
    setUser(null)
    setToken(null)
  }

  return (
    <AuthContext.Provider value={{ user, token, loading, signInWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider')
  return ctx
}
